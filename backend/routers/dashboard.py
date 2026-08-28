from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import uuid

from database import get_db
from models.user import User
from models.profile import WellbeingProfile, DimensionScore
from models.pattern import DetectedPattern, Intervention, Feedback
from models.message import Conversation, Message
from services.graph_manager import GraphManager
from services.risk_classifier import RiskClassifier

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/{user_id}")
async def get_dashboard_data(user_id: str, db: Session = Depends(get_db)):
    # 1. Look up user
    try:
        u_uuid = uuid.UUID(user_id)
        user = db.query(User).filter(User.id == u_uuid).first()
    except ValueError:
        user = None

    if not user:
        # Create a default demo user so dashboard immediately displays cleanly
        user = User(
            username=f"teen_{str(uuid.uuid4())[:8]}",
            display_name="Alex (Demo Profile)",
            country_code="IN",
            is_demo=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. Get profile
    profile = db.query(WellbeingProfile).filter(WellbeingProfile.user_id == user.id).first()
    if not profile:
        profile = WellbeingProfile(
            user_id=user.id,
            baseline_social=72.0,
            baseline_family=70.0,
            baseline_academic=68.0,
            baseline_digital=65.0,
            baseline_lifestyle=70.0,
            current_social=68.0,
            current_family=70.0,
            current_academic=60.0,
            current_digital=55.0,
            current_lifestyle=58.0,
            risk_level="CONCERNING"
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    # 3. Time-series dimension trends
    scores_history = (
        db.query(DimensionScore)
        .filter(DimensionScore.profile_id == profile.id)
        .order_by(DimensionScore.recorded_at.asc())
        .limit(20)
        .all()
    )

    history_points = []
    if scores_history:
        for s in scores_history:
            history_points.append({
                "timestamp": s.recorded_at.strftime("%b %d, %H:%M"),
                "social": s.social,
                "family": s.family,
                "academic": s.academic,
                "digital": s.digital,
                "lifestyle": s.lifestyle,
                "emotions": s.emotions or []
            })
    else:
        # Seed realistic starting sample points for initial visualization
        history_points = [
            {"timestamp": "Day 1", "social": 75.0, "family": 72.0, "academic": 70.0, "digital": 68.0, "lifestyle": 74.0, "emotions": ["calm"]},
            {"timestamp": "Day 2", "social": 72.0, "family": 70.0, "academic": 65.0, "digital": 62.0, "lifestyle": 68.0, "emotions": ["hopeful"]},
            {"timestamp": "Day 3", "social": 68.0, "family": 70.0, "academic": 60.0, "digital": 55.0, "lifestyle": 58.0, "emotions": ["tired", "anxious"]}
        ]

    # 4. Detected Patterns
    patterns = (
        db.query(DetectedPattern)
        .filter(DetectedPattern.user_id == user.id)
        .order_by(DetectedPattern.last_detected.desc())
        .all()
    )
    patterns_list = [
        {
            "id": str(p.id),
            "title": p.title,
            "description": p.description,
            "category": p.category,
            "severity": p.severity,
            "dimensions_involved": p.dimensions_involved or [],
            "evidence_snippets": p.evidence_snippets or [],
            "occurrence_count": p.occurrence_count
        }
        for p in patterns
    ]
    if not patterns_list:
        patterns_list = [
            {
                "id": "demo-pat-1",
                "title": "Academic Pressure & Late-Night Screen Cycle",
                "description": "Exam preparation stress correlates with late-night phone browsing, resulting in disrupted sleep and compounding fatigue.",
                "category": "cross_dimensional",
                "severity": "medium",
                "dimensions_involved": ["academic", "digital", "lifestyle"],
                "evidence_snippets": ["Study workload causing stress", "Compulsive late-night screen time", "Fatigue and sleep reduction"],
                "occurrence_count": 2
            }
        ]

    # 5. Graph Data
    graph_data = GraphManager.get_or_initialize_graph(db, user.id)

    # 6. Interventions History
    interventions = (
        db.query(Intervention)
        .filter(Intervention.user_id == user.id)
        .order_by(Intervention.created_at.desc())
        .limit(10)
        .all()
    )
    interventions_list = [
        {
            "id": str(i.id),
            "type": i.intervention_type,
            "title": i.title,
            "content": i.content,
            "risk_level": i.risk_level_triggered,
            "date": i.created_at.strftime("%b %d, %Y")
        }
        for i in interventions
    ]

    # 7. Safety Status & Helplines
    _, _, safety_guidance = RiskClassifier.evaluate(
        text="",
        dimension_scores={
            "social": profile.current_social,
            "family": profile.current_family,
            "academic": profile.current_academic,
            "digital": profile.current_digital,
            "lifestyle": profile.current_lifestyle
        }
    )
    helplines = RiskClassifier.get_helpline_info(user.country_code or "IN")

    return {
        "user": {
            "id": str(user.id),
            "display_name": user.display_name,
            "country_code": user.country_code,
            "age_group": user.age_group,
            "session_count": profile.session_count
        },
        "dimensions": {
            "social": {"current": profile.current_social, "baseline": profile.baseline_social, "delta": round(profile.current_social - profile.baseline_social, 1)},
            "family": {"current": profile.current_family, "baseline": profile.baseline_family, "delta": round(profile.current_family - profile.baseline_family, 1)},
            "academic": {"current": profile.current_academic, "baseline": profile.baseline_academic, "delta": round(profile.current_academic - profile.baseline_academic, 1)},
            "digital": {"current": profile.current_digital, "baseline": profile.baseline_digital, "delta": round(profile.current_digital - profile.baseline_digital, 1)},
            "lifestyle": {"current": profile.current_lifestyle, "baseline": profile.baseline_lifestyle, "delta": round(profile.current_lifestyle - profile.baseline_lifestyle, 1)},
        },
        "trends": history_points,
        "patterns": patterns_list,
        "graph": graph_data,
        "interventions": interventions_list,
        "safety": {
            "risk_level": profile.risk_level,
            "guidance": safety_guidance,
            "helplines": helplines
        }
    }
