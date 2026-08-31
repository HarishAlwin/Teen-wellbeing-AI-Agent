import os
import logging
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy.orm import Session
from models.escalation import Escalation

logger = logging.getLogger("escalation_service")

# ── Feature flags ──────────────────────────────────────────────────────────────
# Set ESCALATION_EMAIL_ENABLED=true to enable SMTP admin/counselor alerts
ESCALATION_EMAIL_ENABLED = os.getenv("ESCALATION_EMAIL_ENABLED", "false").lower() == "true"

# Set EMERGENCY_CONTACT_NOTIFY_ENABLED=true to also notify the user's personal
# emergency contacts on IMMEDIATE_SAFETY events. Off by default.
EMERGENCY_CONTACT_NOTIFY_ENABLED = os.getenv("EMERGENCY_CONTACT_NOTIFY_ENABLED", "false").lower() == "true"

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ALERT_RECIPIENT_EMAIL = os.getenv("ALERT_RECIPIENT_EMAIL", "")


class EscalationService:
    """
    Automated escalation service for HIGH_CONCERN and IMMEDIATE_SAFETY risk events.

    Architecture:
    1. Every high-risk message ALWAYS creates a DB Escalation record (audit trail).
    2. Automated priority voice call & SMS dispatch to designated emergency contact on IMMEDIATE_SAFETY.
    3. Admin/counselor email is feature-flagged off by default (ESCALATION_EMAIL_ENABLED=false).
    4. Per-user emergency contact notification is separately flagged (EMERGENCY_CONTACT_NOTIFY_ENABLED=false).
    5. All channels run in parallel for IMMEDIATE_SAFETY.
    6. This service is intentionally NOT the primary safety floor — RiskClassifier regex
       rules run independently and win if they disagree upward (see routers/chat.py).
    """

    # Risk levels that trigger automated escalation
    ESCALATION_TRIGGER_LEVELS = {"HIGH_CONCERN", "IMMEDIATE_SAFETY"}

    @classmethod
    def trigger(
        cls,
        db: Session,
        user_id: uuid.UUID,
        conversation_id: Optional[uuid.UUID],
        risk_level: str,
        reason: str,
        user_message: str = "",
    ) -> Optional[Escalation]:

        """
        Trigger an escalation event. Always logs to DB. Optionally sends email if enabled.

        Notification channels (all parallel, none replaces another):
          1. DB audit record — always created
          2. Admin/counselor SMTP — if ESCALATION_EMAIL_ENABLED=true
          3. Per-user emergency contacts — if EMERGENCY_CONTACT_NOTIFY_ENABLED=true
             AND risk_level is IMMEDIATE_SAFETY

        Returns the created Escalation record, or None if risk level doesn't warrant escalation.
        """
        if risk_level not in cls.ESCALATION_TRIGGER_LEVELS:
            return None

        channel = "helpline_demo_log"
        status = "pending"
        triggered_at = datetime.utcnow()

        # ── Channel 1: Automated Phone Call & SMS Dispatch ─────────────────────
        if risk_level == "IMMEDIATE_SAFETY":
            from services.emergency_dispatcher import EmergencyDispatcher
            try:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    loop.create_task(
                        EmergencyDispatcher.dispatch(
                            user_id=str(user_id),
                            user_message=user_message,
                            risk_level=risk_level,
                            reason=reason
                        )
                    )
                else:
                    asyncio.run(
                        EmergencyDispatcher.dispatch(
                            user_id=str(user_id),
                            user_message=user_message,
                            risk_level=risk_level,
                            reason=reason
                        )
                    )
                channel = "auto_voice_call,auto_sms"
                status = "dispatched"
            except Exception as e:
                logger.error(f"[EscalationService] EmergencyDispatcher error: {e}", exc_info=True)


        # ── Channel 2: Admin/counselor SMTP alert ──────────────────────────────
        if ESCALATION_EMAIL_ENABLED:
            email_sent = cls._send_email_alert(
                user_id=user_id,
                risk_level=risk_level,
                reason=reason,
                triggered_at=triggered_at,
            )
            if email_sent:
                channel += ",smtp_email"
                status = "notified"
            else:
                logger.warning("[EscalationService] Admin email delivery failed, falling back to demo log.")

        # ── Channel 3: Per-user emergency contacts (IMMEDIATE_SAFETY only) ─────
        if EMERGENCY_CONTACT_NOTIFY_ENABLED and risk_level == "IMMEDIATE_SAFETY":
            contacts_notified = cls._notify_emergency_contacts(
                db=db,
                user_id=user_id,
                risk_level=risk_level,
                reason=reason,
                triggered_at=triggered_at,
            )
            if contacts_notified > 0:
                # Append to channel string so it's visible in the audit record
                channel = channel + f",emergency_contacts({contacts_notified})"
                status = "notified"

        # ── Always persist escalation record to DB ─────────────────────────────
        escalation = Escalation(
            user_id=user_id,
            conversation_id=conversation_id,
            risk_level=risk_level,
            reason=reason,
            triggered_at=triggered_at,
            notified_channel=channel,
            status=status,
        )
        db.add(escalation)
        db.flush()  # Flush so we get the ID without committing the outer transaction


        logger.warning(
            f"[EscalationService] ESCALATION TRIGGERED | "
            f"user={user_id} | level={risk_level} | channel={channel} | "
            f"reason={reason[:120]}"
        )

        return escalation

    @classmethod
    def _notify_emergency_contacts(
        cls,
        db: Session,
        user_id: uuid.UUID,
        risk_level: str,
        reason: str,
        triggered_at: datetime,
    ) -> int:
        """
        Notify all active emergency contacts for a user via SMTP.
        Returns the number of contacts successfully notified.
        Only called when EMERGENCY_CONTACT_NOTIFY_ENABLED=true.
        """
        from models.emergency_contact import EmergencyContact

        if not all([SMTP_HOST, SMTP_USER, SMTP_PASS]):
            logger.error("[EscalationService] SMTP credentials incomplete — cannot notify emergency contacts.")
            return 0

        contacts = db.query(EmergencyContact).filter(
            EmergencyContact.user_id == user_id,
            EmergencyContact.is_active == True,
            EmergencyContact.email != None,
        ).all()

        if not contacts:
            logger.info(f"[EscalationService] No active email contacts for user {user_id}")
            return 0

        notified = 0
        for contact in contacts:
            try:
                subject = f"[Important] Safety Alert for a Teen You Support"
                body = (
                    f"Dear {contact.name},\n\n"
                    f"You are registered as an emergency contact for a teenager using the "
                    f"Teen Wellbeing Intelligence system.\n\n"
                    f"Our system has detected signals that may indicate an immediate safety concern "
                    f"requiring human support. This is an automated alert.\n\n"
                    f"Please reach out to them as soon as possible to check in and offer support.\n\n"
                    f"Detected at: {triggered_at.isoformat()}\n\n"
                    f"If you believe this is a crisis situation, please contact emergency services (112 / 911).\n\n"
                    f"---\n"
                    f"This alert was sent by the Teen Wellbeing Intelligence system.\n"
                    f"You were contacted because you are registered as a {contact.contact_type} "
                    f"for this user.\n"
                    f"To be removed from notifications, ask the teen to manage their emergency contacts."
                )

                msg = MIMEMultipart()
                msg["From"] = SMTP_USER
                msg["To"] = contact.email
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain"))

                with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                    server.ehlo()
                    server.starttls()
                    server.login(SMTP_USER, SMTP_PASS)
                    server.sendmail(SMTP_USER, contact.email, msg.as_string())

                logger.info(
                    f"[EscalationService] Emergency contact notified: {contact.name} "
                    f"({contact.email}) for user {user_id}"
                )
                notified += 1

            except Exception as e:
                logger.error(
                    f"[EscalationService] Failed to notify emergency contact "
                    f"{contact.name} ({contact.email}): {e}"
                )

        return notified

    @classmethod
    def _send_email_alert(
        cls,
        user_id: uuid.UUID,
        risk_level: str,
        reason: str,
        triggered_at: datetime,
    ) -> bool:
        """
        SMTP email delivery to the admin/counselor inbox.
        Returns True if email was sent successfully, False otherwise.

        To enable: set ESCALATION_EMAIL_ENABLED=true and configure SMTP_HOST,
        SMTP_USER, SMTP_PASS, ALERT_RECIPIENT_EMAIL in your .env file.
        """
        if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, ALERT_RECIPIENT_EMAIL]):
            logger.error("[EscalationService] SMTP credentials incomplete — email not sent.")
            return False

        try:
            subject = f"[Teen Wellbeing Alert] {risk_level} — Immediate Attention Required"
            body = (
                f"An automated escalation has been triggered.\n\n"
                f"Risk Level: {risk_level}\n"
                f"Triggered At: {triggered_at.isoformat()}\n"
                f"User ID: {user_id}\n\n"
                f"Reason:\n{reason}\n\n"
                f"---\n"
                f"Please review this case in the counselor dashboard at /alerts.\n"
                f"This alert was generated by the Teen Wellbeing Intelligence system."
            )

            msg = MIMEMultipart()
            msg["From"] = SMTP_USER
            msg["To"] = ALERT_RECIPIENT_EMAIL
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_USER, ALERT_RECIPIENT_EMAIL, msg.as_string())

            logger.info(f"[EscalationService] Alert email sent to {ALERT_RECIPIENT_EMAIL}")
            return True

        except Exception as e:
            logger.error(f"[EscalationService] SMTP error: {e}")
            return False


