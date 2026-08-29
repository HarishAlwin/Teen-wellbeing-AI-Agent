import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from database import Base
from models.guid import GUID


class Escalation(Base):
    """
    Records every automated escalation event triggered by HIGH_CONCERN
    or IMMEDIATE_SAFETY risk classification. This table is the audit trail
    for counselor/guardian review — NOT visible to the teen user themselves.
    """
    __tablename__ = "escalations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(GUID, nullable=True)

    # Risk level that triggered this escalation
    risk_level = Column(String(30), nullable=False)

    # Human-readable explanation of why escalation was triggered
    reason = Column(Text, nullable=False)

    # Timestamp of escalation event
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Channel used for notification (e.g. "helpline_demo_log", "smtp_email")
    notified_channel = Column(String(100), default="helpline_demo_log", nullable=False)

    # Status of the escalation: "pending" | "notified" | "acknowledged" | "resolved"
    status = Column(String(30), default="pending", nullable=False)
