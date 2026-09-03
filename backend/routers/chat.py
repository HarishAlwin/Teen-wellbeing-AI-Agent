import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from database import get_db, SessionLocal
from models.user import User
from models.profile import WellbeingProfile, DimensionScore
from models.message import Conversation, Message
from models.pattern import DetectedPattern, Intervention, Feedback
from services.risk_classifier import RiskClassifier
from services.wellbeing_analyzer import WellbeingAnalyzer
from services.pattern_detector import PatternDetector
from services.graph_manager import GraphManager
from services.llm_agent import LLMAgent
from services.escalation_service import EscalationService

logger = logging.getLogger("aura.chat")

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


def _run_escalation_background(user_id, conversation_id, risk_level: str, reasons: List[str]):
    """
    Runs in a BackgroundTask after the HTTP response has already been sent,
    so escalation (including any live Twilio call/SMS) never delays the
    teen's chat reply. Uses its own DB session since the request-scoped
    session from get_db() is closed by the time this runs.
    """
    db = SessionLocal()
    try:
        EscalationService.handle_escalation(
            db=db,
            user_id=user_id,
            conversation_id=conversation_id,
            risk_level=risk_level,
            reasons=reasons,
        )
    except Exception:
        logger.exception("Escalation background task failed")
    finally:
        db.close()


@router.post("")
async def send_message(req: ChatRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

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

    # 6. Safety & Risk Classification — deterministic regex/threshold engine.
    # This is the SAFETY FLOOR. It runs independently of the LLM and its
    # result can only ever be escalated upward by the LLM below, never
    # downgraded. This guarantees crisis-language detection keeps working
    # even if the LLM call fails, times out, or misjudges severity.
    risk_level, risk_reasons, safety_guidance = RiskClassifier.evaluate(
        text=req.message,
        dimension_scores=analysis["updated_scores"],
        score_deltas=analysis["score_deltas"]
    )

    # 7. Fetch recent history for context
    past_messages = db.query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.created_at.asc()).all()
    history_formatted = [{"role": m.role, "content": m.content} for m in past_messages]

    # 8. Pattern Detection (rule-based)
    active_patterns_raw = PatternDetector.detect_patterns(
        current_scores=analysis["updated_scores"],
        baseline_scores=baseline_scores,
        signals=analysis["dimension_signals"],
        emotions=analysis["emotions"]
    )

    # 9. LLM Generation — wrapped defensively so a Gemini failure degrades to
    # the deterministic fallback response instead of bubbling up as a raw
    # exception (LLMAgent already does this internally, but we log here too
    # so failures are visible in the backend terminal).
    try:
        llm_output = LLMAgent.generate_response(
            user_message=req.message,
            conversation_history=history_formatted,
            current_scores=analysis["updated_scores"],
            active_patterns=active_patterns_raw,
            risk_level=risk_level,
            safety_guidance=safety_guidance
        )
    except Exception:
        logger.exception("LLMAgent.generate_response raised unexpectedly; using fallback")
        llm_output = LLMAgent._fallback_response(
            req.message, analysis["updated_scores"], active_patterns_raw, risk_level, safety_guidance
        )

    # 9b. Agentic tool-use phase — the model itself decides (via real Gemini
    # function calling) whether to check pattern history, flag a risk level,
    # and/or request escalation. This is what makes the risk/escalation
    # decision genuinely agentic rather than only pre-computed and handed
    # to the LLM. Wrapped defensively: if this fails or Gemini is
    # unavailable, we simply proceed without its input — the rule-based
    # floor and the structured generate_response() call above still work.
    try:
        agentic_result = LLMAgent.run_agentic_reasoning(
            user_message=req.message,
            conversation_history=history_formatted,
            active_patterns=active_patterns_raw,
        )
    except Exception:
        logger.exception("Agentic tool-use phase raised unexpectedly; continuing without it")
        agentic_result = {"risk_flag": None, "escalation_requested": False, "escalation_reason": None}

    # 9c. Reconcile every risk signal we now have. The rule-based floor
    # (risk_level, set in step 6) can only be escalated UPWARD by either the
    # LLM's structured risk_assessment or its agentic flag_risk_level tool
    # call — never downgraded. This is the core "LLM drives judgment, rules
    # are a safety floor" behavior.
    _SEVERITY = {"NORMAL": 0, "CONCERNING": 1, "HIGH_CONCERN": 2, "IMMEDIATE_SAFETY": 3}

    candidate_levels = [risk_level]
    llm_risk_assessment = llm_output.get("risk_assessment") or {}
    if llm_risk_assessment.get("level"):
        candidate_levels.append(llm_risk_assessment["level"])
    if agentic_result.get("risk_flag", {}) and agentic_result["risk_flag"].get("level"):
        candidate_levels.append(agentic_result["risk_flag"]["level"])

    highest_level = max(candidate_levels, key=lambda lvl: _SEVERITY.get(lvl, 0))

    if agentic_result.get("escalation_requested"):
        # The model explicitly decided a human should be notified — honor
        # that by ensuring we're at least at HIGH_CONCERN, and record why.
        highest_level = max(highest_level, "HIGH_CONCERN", key=lambda lvl: _SEVERITY.get(lvl, 0))
        if agentic_result.get("escalation_reason"):
            risk_reasons.append(f"Agent requested escalation: {agentic_result['escalation_reason']}")

    if highest_level != risk_level:
        if llm_risk_assessment.get("reasoning"):
            risk_reasons.append(f"LLM assessment: {llm_risk_assessment['reasoning']}")
        risk_level = highest_level
        safety_guidance = RiskClassifier._get_guidance(risk_level)

    # 9d. Merge any patterns the LLM itself observed (from reasoning over
    # the full conversation) into the rule-based pattern list, tagged with
    # source="llm" so it's clear which is which. This is what makes pattern
    # detection adaptive instead of only the ~6 fixed if/else templates.
    active_patterns_raw = PatternDetector.merge_llm_patterns(
        active_patterns_raw, llm_output.get("pattern_observations", [])
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

    # 11. Trigger escalation as a background task if risk is high enough.
    # This fires AFTER we've already prepared the response below — the
    # actual dispatch happens post-response via BackgroundTasks so the
    # teenager's reply is never delayed by a call/SMS attempt.
    if EscalationService.should_escalate(risk_level):
        background_tasks.add_task(
            _run_escalation_background,
            user.id,
            conversation.id,
            risk_level,
            risk_reasons,
        )
        logger.warning(
            "Escalation queued: user_id=%s risk_level=%s reasons=%s",
            user.id, risk_level, risk_reasons
        )

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
