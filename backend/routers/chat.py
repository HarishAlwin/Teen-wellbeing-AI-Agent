from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from database import get_db
from models.user import User
from models.profile import WellbeingProfile, DimensionScore
from models.message import Conversation, Message
from models.pattern import DetectedPattern, Intervention, Feedback
from services.risk_classifier import RiskClassifier
from services.wellbeing_analyzer import WellbeingAnalyzer
from services.pattern_detector import PatternDetector
from services.graph_manager import GraphManager
from services.llm_agent import LLMAgent

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    message: str
    country_code: Optional[str] = "IN"

class FeedbackRequest(BaseModel):
    user_id: str
    intervention_id: Optional[str] = None
    rating: str  # helpful | somewhat_helpful | not_helpful
    comment: Optional[str] = None

@router.post("")
async def send_message(req: ChatRequest, db: Session = Depends(get_db)):
    # 1. Resolve or create user
    user = None
    if req.user_id:
        try:
            u_uuid = uuid.UUID(req.user_id)
            user = db.query(User).filter(User.id == u_uuid).first()
        except ValueError:
            pass

    if not user:
        user = User(
            username=f"teen_{str(uuid.uuid4())[:8]}",
            display_name="Alex",
            country_code=req.country_code or "IN",
            is_demo=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. Resolve or create profile
    profile = db.query(WellbeingProfile).filter(WellbeingProfile.user_id == user.id).first()
    if not profile:
        profile = WellbeingProfile(
            user_id=user.id,
            baseline_social=72.0,
            baseline_family=70.0,
            baseline_academic=68.0,
            baseline_digital=65.0,
            baseline_lifestyle=70.0,
            current_social=72.0,
            current_family=70.0,
            current_academic=68.0,
            current_digital=65.0,
            current_lifestyle=70.0
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    # 3. Resolve or create conversation
    conversation = None
    if req.conversation_id:
        try:
            c_uuid = uuid.UUID(req.conversation_id)
            conversation = db.query(Conversation).filter(Conversation.id == c_uuid).first()
        except ValueError:
            pass

    if not conversation:
        conversation = Conversation(user_id=user.id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 4. Current scores & baselines
    current_scores = {
        "social": profile.current_social,
        "family": profile.current_family,
        "academic": profile.current_academic,
        "digital": profile.current_digital,
        "lifestyle": profile.current_lifestyle
    }
    baseline_scores = {
        "social": profile.baseline_social,
        "family": profile.baseline_family,
        "academic": profile.baseline_academic,
        "digital": profile.baseline_digital,
        "lifestyle": profile.baseline_lifestyle
    }

    # 5. Pre-analyze user text signals
    analysis = WellbeingAnalyzer.analyze_message(req.message, current_scores)

    # 6. Safety & Risk Classification
    risk_level, risk_reasons, safety_guidance = RiskClassifier.evaluate(
        text=req.message,
        dimension_scores=analysis["updated_scores"],
        score_deltas=analysis["score_deltas"]
    )

    # 7. Fetch recent history for context
    past_messages = db.query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.created_at.asc()).all()
    history_formatted = [{"role": m.role, "content": m.content} for m in past_messages]

    # 8. Pattern Detection
    active_patterns_raw = PatternDetector.detect_patterns(
        current_scores=analysis["updated_scores"],
        baseline_scores=baseline_scores,
        signals=analysis["dimension_signals"],
        emotions=analysis["emotions"]
    )

    # 9. LLM Generation
    llm_output = LLMAgent.generate_response(
        user_message=req.message,
        conversation_history=history_formatted,
        current_scores=analysis["updated_scores"],
        active_patterns=active_patterns_raw,
        risk_level=risk_level,
        safety_guidance=safety_guidance
    )

    # Re-evaluate with LLM insights if LLM spotted higher risk
    if llm_output.get("suggested_risk_level") in ["HIGH_CONCERN", "IMMEDIATE_SAFETY"] and risk_level == "NORMAL":
        risk_level, risk_reasons, safety_guidance = RiskClassifier.evaluate(
            text=req.message,
            llm_suggested_risk=llm_output.get("suggested_risk_level")
        )

    # 10. Update Profile & Persist Scores
    profile.current_social = analysis["updated_scores"]["social"]
    profile.current_family = analysis["updated_scores"]["family"]
    profile.current_academic = analysis["updated_scores"]["academic"]
    profile.current_digital = analysis["updated_scores"]["digital"]
    profile.current_lifestyle = analysis["updated_scores"]["lifestyle"]
    profile.risk_level = risk_level
    profile.session_count = (profile.session_count or 0) + 1
    profile.updated_at = datetime.utcnow()

    # Save time-series dimension score
    dim_score_rec = DimensionScore(
        profile_id=profile.id,
        conversation_id=conversation.id,
        social=profile.current_social,
        family=profile.current_family,
        academic=profile.current_academic,
        digital=profile.current_digital,
        lifestyle=profile.current_lifestyle,
        signals=analysis["dimension_signals"],
        emotions=analysis["emotions"]
    )
    db.add(dim_score_rec)

    # Save User Message
    user_msg_rec = Message(
        conversation_id=conversation.id,
        role="user",
        content=req.message,
        emotions_detected=analysis["emotions"],
        dimension_signals=analysis["dimension_signals"],
        risk_level_at_send=risk_level
    )
    db.add(user_msg_rec)

    # Save Assistant Message
    assistant_msg_rec = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=llm_output.get("response_text", ""),
        emotions_detected=[],
        dimension_signals={},
        risk_level_at_send=risk_level
    )
    db.add(assistant_msg_rec)

    # Save Patterns
    for pat in active_patterns_raw:
        existing_pat = db.query(DetectedPattern).filter(
            DetectedPattern.user_id == user.id,
            DetectedPattern.title == pat["title"]
        ).first()

        if existing_pat:
            existing_pat.occurrence_count += 1
            existing_pat.last_detected = datetime.utcnow()
            existing_pat.is_active = True
        else:
            new_pat = DetectedPattern(
                user_id=user.id,
                title=pat["title"],
                description=pat["description"],
                category=pat["category"],
                severity=pat["severity"],
                dimensions_involved=pat["dimensions_involved"],
                evidence_snippets=pat["evidence_snippets"],
                is_active=True
            )
            db.add(new_pat)

    # Save Intervention if generated
    intervention_data = llm_output.get("intervention", {})
    created_intervention = None
    if intervention_data and intervention_data.get("needed", False):
        intervention_rec = Intervention(
            user_id=user.id,
            conversation_id=conversation.id,
            intervention_type=intervention_data.get("type", "reflective_question"),
            title=intervention_data.get("title", "Support Suggestion"),
            content=intervention_data.get("content", ""),
            risk_level_triggered=risk_level
        )
        db.add(intervention_rec)
        db.commit()
        db.refresh(intervention_rec)
        created_intervention = {
            "id": str(intervention_rec.id),
            "type": intervention_rec.intervention_type,
            "title": intervention_rec.title,
            "content": intervention_rec.content
        }

    # Update Graph
    GraphManager.update_graph_from_patterns(
        db=db,
        user_id=user.id,
        patterns=active_patterns_raw,
        dimension_scores=analysis["updated_scores"]
    )
    graph_data = GraphManager.get_or_initialize_graph(db, user.id)

    db.commit()

    helplines = RiskClassifier.get_helpline_info(user.country_code or "IN")

    return {
        "user_id": str(user.id),
        "conversation_id": str(conversation.id),
        "response_text": llm_output.get("response_text", ""),
        "emotions_detected": analysis["emotions"],
        "dimension_scores": analysis["updated_scores"],
        "score_deltas": analysis["score_deltas"],
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
        "safety_guidance": safety_guidance,
        "helplines": helplines if safety_guidance.get("show_helplines") else None,
        "active_patterns": active_patterns_raw,
        "intervention": created_intervention,
        "graph": graph_data
    }

@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    try:
        u_uuid = uuid.UUID(req.user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    i_uuid = None
    if req.intervention_id:
        try:
            i_uuid = uuid.UUID(req.intervention_id)
        except ValueError:
            pass

    fb = Feedback(
        user_id=u_uuid,
        intervention_id=i_uuid,
        rating=req.rating,
        comment=req.comment
    )
    db.add(fb)

    # Update user preferences in profile
    profile = db.query(WellbeingProfile).filter(WellbeingProfile.user_id == u_uuid).first()
    if profile:
        prefs = dict(profile.preferences or {})
        prefs[f"feedback_rating_{req.rating}"] = prefs.get(f"feedback_rating_{req.rating}", 0) + 1
        profile.preferences = prefs

    db.commit()
    return {"status": "success", "message": "Feedback recorded. Thank you!"}
