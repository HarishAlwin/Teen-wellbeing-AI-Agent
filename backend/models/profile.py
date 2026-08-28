import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base
from models.guid import GUID

class WellbeingProfile(Base):
    __tablename__ = "wellbeing_profiles"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), unique=True, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Baseline scores
    baseline_social = Column(Float, default=70.0)
    baseline_family = Column(Float, default=70.0)
    baseline_academic = Column(Float, default=70.0)
    baseline_digital = Column(Float, default=70.0)
    baseline_lifestyle = Column(Float, default=70.0)

    # Current scores
    current_social = Column(Float, default=70.0)
    current_family = Column(Float, default=70.0)
    current_academic = Column(Float, default=70.0)
    current_digital = Column(Float, default=70.0)
    current_lifestyle = Column(Float, default=70.0)

    # Risk level: NORMAL | CONCERNING | HIGH_CONCERN | IMMEDIATE_SAFETY
    risk_level = Column(String(30), default="NORMAL")

    recurring_themes = Column(JSON, default=list)
    positive_changes = Column(JSON, default=list)
    concerning_changes = Column(JSON, default=list)
    preferences = Column(JSON, default=dict)
    session_count = Column(Integer, default=0)

    user = relationship("User", back_populates="profile")
    dimension_scores = relationship("DimensionScore", back_populates="profile", cascade="all, delete-orphan")


class DimensionScore(Base):
    __tablename__ = "dimension_scores"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    profile_id = Column(GUID, ForeignKey("wellbeing_profiles.id"), nullable=False)
    conversation_id = Column(GUID, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    social = Column(Float, default=70.0)
    family = Column(Float, default=70.0)
    academic = Column(Float, default=70.0)
    digital = Column(Float, default=70.0)
    lifestyle = Column(Float, default=70.0)

    signals = Column(JSON, default=dict)
    emotions = Column(JSON, default=list)

    profile = relationship("WellbeingProfile", back_populates="dimension_scores")
