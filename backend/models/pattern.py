import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, JSON, Boolean, Text
from database import Base
from models.guid import GUID

class DetectedPattern(Base):
    __tablename__ = "detected_patterns"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), default="cross_dimensional")
    severity = Column(String(30), default="medium")
    dimensions_involved = Column(JSON, default=list)
    evidence_snippets = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    first_detected = Column(DateTime, default=datetime.utcnow)
    last_detected = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    occurrence_count = Column(Float, default=1.0)


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(GUID, nullable=True)
    intervention_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    risk_level_triggered = Column(String(30), default="NORMAL")
    created_at = Column(DateTime, default=datetime.utcnow)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)
    intervention_id = Column(GUID, ForeignKey("interventions.id"), nullable=True)
    rating = Column(String(30), nullable=False) # helpful | somewhat_helpful | not_helpful
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
