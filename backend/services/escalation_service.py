import os
import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("escalation")

# Master switch: keep this OFF during development so no real call/SMS ever
# fires accidentally while testing crisis-language handling. Flip to "true"
# in .env only when you're intentionally demoing/deploying with real credentials.
ESCALATION_ENABLED = os.getenv("ESCALATION_ENABLED", "false").strip().lower() == "true"
HELPLINE_ALERT_NUMBER = os.getenv("HELPLINE_ALERT_NUMBER", "")

# ── CALL-E Configuration (Primary Channel) ───────────────────────────────────
CALLE_API_KEY = os.getenv("CALLE_API_KEY", "")
CALLE_BASE_URL = os.getenv("CALLE_BASE_URL", "https://api.heycall-e.com")
CALLE_RECIPIENT_REGION = os.getenv("CALLE_RECIPIENT_REGION", "IN")
CALLE_RECIPIENT_LOCALE = os.getenv("CALLE_RECIPIENT_LOCALE", "en-IN")

try:
    from calle import CalleClient
    calle_available = bool(CALLE_API_KEY and CALLE_API_KEY != "your_calle_api_key_here")
except ImportError:
    CalleClient = None
    calle_available = False

# ── Twilio Configuration (Fallback Channel) ──────────────────────────────────
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

try:
    from twilio.rest import Client as TwilioClient
    twilio_available = bool(
        TWILIO_ACCOUNT_SID
        and TWILIO_AUTH_TOKEN
        and TWILIO_FROM_NUMBER
        and TWILIO_ACCOUNT_SID != "your_twilio_account_sid_here"
    )
except ImportError:
    TwilioClient = None
    twilio_available = False

# CALL-E Structured Result JSON Schema
CALLE_RESULT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "counselor_reached": {
            "type": "string",
            "enum": ["yes", "no", "unknown"],
            "description": "Whether a human counselor or staff member answered the phone call."
        },
        "acknowledged": {
            "type": "string",
            "enum": ["yes", "no", "unknown"],
            "description": "Whether the counselor acknowledged receiving and understanding the wellbeing alert."
        },
        "recommended_next_step": {
            "type": "string",
            "enum": [
                "dispatch_now",
                "schedule_followup",
                "no_action_needed",
                "retry_later",
                "unknown"
            ],
            "description": "The recommended next course of action determined during the call with the counselor."
        },
        "notes": {
            "type": "string",
            "description": "Key takeaways, direct guidance, or notes from the conversation with the counselor."
        }
    },
    "required": ["counselor_reached", "acknowledged", "recommended_next_step", "notes"]
}


class EscalationService:
    """
    Handles notification when a user's risk level reaches HIGH_CONCERN or
    IMMEDIATE_SAFETY. Always writes an audit-trail Escalation record.

    Escalation channel priority:
      1. CALL-E AI Call (if CALLE_API_KEY is configured) — Primary Channel
      2. Twilio SMS + Voice Call (if Twilio credentials are configured) — Fallback
      3. logged_only (if neither live provider is configured)
    """

    @classmethod
    def should_escalate(cls, risk_level: str) -> bool:
        return risk_level in ("HIGH_CONCERN", "IMMEDIATE_SAFETY")

    @classmethod
    def handle_escalation(
        cls,
        db: Session,
        user_id,
        conversation_id,
        risk_level: str,
        reasons: List[str],
    ) -> Dict[str, Any]:
        """
        Synchronous entry point, intended to be called from a FastAPI
        BackgroundTask so it never delays the chat response returned to
        the user. Creates the audit record, then attempts live delivery
        via CALL-E (primary) or Twilio (fallback).
        """
        from models.escalation import Escalation

        reasons_text = "; ".join(reasons) if reasons else "Risk thresholds met."

        record = Escalation(
            user_id=user_id,
            conversation_id=conversation_id,
            risk_level=risk_level,
            reasons=reasons_text,
            notified_channel="logged_only",
            status="triggered",
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        logger.warning(
            "[ESCALATION] risk_level=%s user_id=%s reasons=%s (live_delivery_enabled=%s, calle_available=%s, twilio_available=%s)",
            risk_level, user_id, reasons_text, ESCALATION_ENABLED, calle_available, twilio_available
        )

        if not ESCALATION_ENABLED:
            return {"status": "logged_only", "reason": "ESCALATION_ENABLED is false"}

        if not HELPLINE_ALERT_NUMBER:
            record.status = "failed"
            record.delivery_error = "HELPLINE_ALERT_NUMBER not set"
            db.commit()
            return {"status": "failed", "reason": "no_alert_number"}

        # ── 1. PRIMARY CHANNEL: CALL-E AI Phone Calling ──────────────────────
        if calle_available and CalleClient:
            try:
                task_instruction = (
                    f"Call the on-call counselor or student support staff regarding a student using Aura (an AI teen wellbeing companion). "
                    f"Inform them that the system detected an urgent risk level of '{risk_level}'. "
                    f"State the detected situation reasons: '{reasons_text}'. "
                    f"Ask the counselor to confirm if they can follow up with the student, whether they acknowledge this alert, "
                    f"and ask for any immediate guidance or recommended next action."
                )

                recipients = [
                    {
                        "phones": [HELPLINE_ALERT_NUMBER],
                        "region": CALLE_RECIPIENT_REGION,
                        "locale": CALLE_RECIPIENT_LOCALE,
                    }
                ]

                metadata = {
                    "app": "aura-teen-wellbeing",
                    "user_id": str(user_id) if user_id else "",
                    "conversation_id": str(conversation_id) if conversation_id else "",
                    "risk_level": risk_level,
                }

                idempotency_key = f"aura-escalation-{user_id}-{conversation_id}-{risk_level}"

                with CalleClient(api_key=CALLE_API_KEY, base_url=CALLE_BASE_URL) as client:
                    call_result = client.calls.create_and_wait(
                        task=task_instruction,
                        recipients=recipients,
                        result_schema=CALLE_RESULT_SCHEMA,
                        metadata=metadata,
                        idempotency_key=idempotency_key,
                    )

                record.notified_channel = "calle"
                record.calle_call_id = str(call_result.get("id")) if call_result.get("id") else None
                record.calle_task_completed = bool(call_result.get("task_completed", False))
                
                structured = call_result.get("structured_result")
                if structured is not None:
                    record.calle_structured_result = json.dumps(structured)
                
                call_status = call_result.get("status", "completed")
                if call_status == "completed":
                    record.status = "notified"
                elif call_status == "failed":
                    record.status = "failed"
                    record.delivery_error = "CALL-E call ended with failed status"
                else:
                    record.status = "notified"

                db.commit()
                logger.info("[ESCALATION] CALL-E call completed successfully: id=%s task_completed=%s", record.calle_call_id, record.calle_task_completed)
                return {
                    "status": record.status,
                    "channel": "calle",
                    "call_id": record.calle_call_id,
                    "task_completed": record.calle_task_completed,
                    "structured_result": structured,
                }

            except Exception as e:
                record.status = "failed"
                record.delivery_error = f"CALL-E call failed: {str(e)}"
                db.commit()
                logger.exception("[ESCALATION] CALL-E execution failed")
                return {"status": "failed", "channel": "calle", "reason": str(e)}

        # ── 2. FALLBACK CHANNEL: Twilio SMS + Voice Call ────────────────────
        if twilio_available and TwilioClient:
            try:
                client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

                sms = client.messages.create(
                    to=HELPLINE_ALERT_NUMBER,
                    from_=TWILIO_FROM_NUMBER,
                    body=(
                        f"AURA ALERT [{risk_level}]: A monitored student has triggered a "
                        f"safety flag. Reasons: {reasons_text}. Please check the Aura "
                        f"alerts dashboard for details."
                    ),
                )

                twiml = (
                    '<Response><Say voice="alice">'
                    f'Alert. A monitored student has triggered an {risk_level.replace("_", " ").lower()} '
                    'safety flag on the Aura wellbeing system. Please check the alerts dashboard immediately.'
                    '</Say></Response>'
                )
                call = client.calls.create(
                    to=HELPLINE_ALERT_NUMBER,
                    from_=TWILIO_FROM_NUMBER,
                    twiml=twiml,
                )

                record.notified_channel = "sms_and_call"
                record.sms_sid = sms.sid
                record.call_sid = call.sid
                record.status = "notified"
                db.commit()

                logger.info("[ESCALATION] Twilio fallback dispatched: sms=%s call=%s", sms.sid, call.sid)
                return {"status": "notified", "channel": "twilio", "sms_sid": sms.sid, "call_sid": call.sid}

            except Exception as e:
                record.status = "failed"
                record.delivery_error = f"Twilio delivery failed: {str(e)}"
                db.commit()
                logger.exception("[ESCALATION] Twilio delivery failed")
                return {"status": "failed", "channel": "twilio", "reason": str(e)}

        # ── 3. NO PROVIDER CONFIGURED ───────────────────────────────────────
        record.status = "failed"
        record.delivery_error = "Neither CALL-E nor Twilio credentials are configured in .env"
        db.commit()
        logger.error("[ESCALATION] Neither CALL-E nor Twilio available for live escalation")
        return {"status": "failed", "reason": "no_escalation_provider_configured"}
