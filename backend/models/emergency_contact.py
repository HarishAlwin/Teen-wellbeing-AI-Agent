"""
backend/models/emergency_contact.py
────────────────────────────────────
Per-user emergency contacts for IMMEDIATE_SAFETY escalation notifications.

Contact types:
  parent         — biological/adoptive parent
  guardian       — legal guardian
  trusted_adult  — teacher, school counselor, older sibling, etc.

Feature-flagged: contacts are stored at onboarding but notifications only fire
when EMERGENCY_CONTACT_NOTIFY_ENABLED=true AND risk level is IMMEDIATE_SAFETY.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from database import Base
from models.guid import GUID


class EmergencyContact(Base):
    """
    Stores a teenager's registered emergency contact(s).
    Only used for IMMEDIATE_SAFETY escalation notifications.

    Consent is captured via the API at registration time — the endpoint
    displays explicit consent language before creating the record.
    """
    __tablename__ = "emergency_contacts"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Contact classification
    contact_type = Column(String(30), nullable=False)  # parent | guardian | trusted_adult

    # Contact details
    name = Column(String(200), nullable=False)
    phone = Column(String(30), nullable=True)
    email = Column(String(255), nullable=True)

    # Explicit consent tracking
    # Consent is given at onboarding when the teen agrees to the notification policy.
    consent_given_at = Column(DateTime, nullable=True)

    # Soft-delete: deactivating a contact stops notifications without losing audit trail
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # ORM relationship (back-populated from User.emergency_contacts)
    from sqlalchemy.orm import relationship
    user = relationship("User", back_populates="emergency_contacts")
