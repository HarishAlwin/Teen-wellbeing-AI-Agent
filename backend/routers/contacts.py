"""
backend/routers/contacts.py
────────────────────────────
Emergency contact management for teen users.

All endpoints require authentication. A user can only manage their own contacts.
Consent language is shown inline in the endpoint description and enforced by
requiring consent_given to be explicitly set to true in the request body.

ESCALATION INTEGRATION:
  When EMERGENCY_CONTACT_NOTIFY_ENABLED=true and risk level is IMMEDIATE_SAFETY,
  EscalationService.trigger() will notify the user's active registered contacts
  IN ADDITION to the admin/counselor channel. The admin channel is never replaced.
"""

import uuid
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models.emergency_contact import EmergencyContact
from auth import get_current_user
from models.user import User

logger = logging.getLogger("contacts_router")
router = APIRouter(prefix="/api/contacts", tags=["Emergency Contacts"])


# ── Consent notice ─────────────────────────────────────────────────────────────
CONSENT_NOTICE = (
    "By adding an emergency contact, you agree that this person may be contacted "
    "by the Teen Wellbeing system ONLY in situations where the AI has detected "
    "an IMMEDIATE SAFETY concern (e.g. crisis language, self-harm signals). "
    "Your emergency contact will NOT be notified for routine check-ins or "
    "CONCERNING risk levels. You can remove contacts at any time."
)


# ── Request / Response schemas ─────────────────────────────────────────────────

class AddContactRequest(BaseModel):
    contact_type: str  # parent | guardian | trusted_adult
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    # User must explicitly set this to true after reading the consent notice
    consent_given: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "contact_type": "parent",
                "name": "Priya Sharma",
                "phone": "+91 98765 43210",
                "email": "priya.sharma@example.com",
                "consent_given": True,
            }
        }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/consent-notice")
async def get_consent_notice():
    """
    Returns the consent notice text that must be shown to the user before
    they add an emergency contact. The /POST endpoint requires consent_given=true.
    """
    return {"consent_notice": CONSENT_NOTICE}


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_contact(
    req: AddContactRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add an emergency contact for the authenticated user.

    CONSENT: The user must set consent_given=true to confirm they have read and
    accepted the notification policy (see GET /api/contacts/consent-notice).
    """
    allowed_types = {"parent", "guardian", "trusted_adult"}
    if req.contact_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"contact_type must be one of: {list(allowed_types)}"
        )

    if not req.consent_given:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "You must read and accept the consent notice before adding an emergency contact. "
                f"Consent notice: {CONSENT_NOTICE}"
            )
        )

    if not req.phone and not req.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one of phone or email must be provided."
        )

    contact = EmergencyContact(
        user_id=current_user.id,
        contact_type=req.contact_type,
        name=req.name,
        phone=req.phone,
        email=req.email,
        consent_given_at=datetime.utcnow(),
        is_active=True,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)

    logger.info(
        f"[Contacts] Emergency contact added for user {current_user.id}: "
        f"{req.name} ({req.contact_type})"
    )
    return {
        "id": str(contact.id),
        "contact_type": contact.contact_type,
        "name": contact.name,
        "phone": contact.phone,
        "email": contact.email,
        "consent_given_at": contact.consent_given_at.isoformat(),
        "is_active": contact.is_active,
        "message": "Emergency contact added. They will only be notified in IMMEDIATE SAFETY situations.",
    }


@router.get("")
async def list_contacts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all active emergency contacts for the authenticated user."""
    contacts = db.query(EmergencyContact).filter(
        EmergencyContact.user_id == current_user.id,
        EmergencyContact.is_active == True,
    ).all()

    return {
        "user_id": str(current_user.id),
        "contacts": [
            {
                "id": str(c.id),
                "contact_type": c.contact_type,
                "name": c.name,
                "phone": c.phone,
                "email": c.email,
                "consent_given_at": c.consent_given_at.isoformat() if c.consent_given_at else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in contacts
        ],
        "consent_notice": CONSENT_NOTICE,
    }


@router.delete("/{contact_id}", status_code=status.HTTP_200_OK)
async def remove_contact(
    contact_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Soft-delete (deactivate) an emergency contact.
    The record is kept for audit purposes but notifications will no longer be sent.
    """
    try:
        c_uuid = uuid.UUID(contact_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid contact ID")

    contact = db.query(EmergencyContact).filter(
        EmergencyContact.id == c_uuid,
        EmergencyContact.user_id == current_user.id,  # ownership check
    ).first()

    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    contact.is_active = False
    db.commit()
    logger.info(f"[Contacts] Contact {contact_id} deactivated for user {current_user.id}")
    return {"id": contact_id, "status": "deactivated", "message": "Emergency contact removed."}
