import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from database import Base
from models.guid import GUID


class Escalation(Base):
    """
    Records every time a HIGH_CONCERN or IMMEDIATE_SAFETY risk level is reached.
    This is the audit trail for human notification, whether the actual call/SMS
    delivery is enabled or not (see services/escalation_service.py).
    """
    __tablename__ = "escalations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(GUID, nullable=True)
    risk_level = Column(String(30), nullable=False)  # HIGH_CONCERN | IMMEDIATE_SAFETY
    reasons = Column(Text, nullable=True)  # human-readable summary of trigger reasons
    notified_channel = Column(String(50), default="logged_only")  # logged_only | sms | call | sms_and_call
    call_sid = Column(String(100), nullable=True)
    sms_sid = Column(String(100), nullable=True)
    calle_call_id = Column(String(100), nullable=True)
    calle_task_completed = Column(Boolean, nullable=True)
    calle_structured_result = Column(Text, nullable=True)
    delivery_error = Column(Text, nullable=True)
    status = Column(String(30), default="triggered")  # triggered | notified | failed | acknowledged
    triggered_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
