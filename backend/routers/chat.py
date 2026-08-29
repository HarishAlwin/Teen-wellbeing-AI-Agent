"""
backend/routers/chat.py
────────────────────────
Main orchestration endpoint for the Teen Wellbeing AI Agent.

SAFETY-CRITICAL RISK DETERMINATION (read carefully):
  Step 1 — RiskClassifier.evaluate() runs on every message.
           Its regex/threshold rules are the MANDATORY SAFETY FLOOR.
           They can only escalate upward; they never downgrade.

  Step 2 — LLMAgent.generate_response() produces risk_assessment.proposed_level
           as the PRIMARY signal for messages that don't already trip the rule floor.

  Step 3 — Final risk level = max(rule_level, llm_level) using the severity ordering:
           NORMAL < CONCERNING < HIGH_CONCERN < IMMEDIATE_SAFETY
           The rule engine can escalate the LLM's proposal UP but NEVER downgrade it.

  Step 4 — EscalationService.trigger() writes a DB record for every HIGH_CONCERN
           or IMMEDIATE_SAFETY outcome, regardless of which source triggered it.
"""

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
from services.escalation_service import EscalationService

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# Risk level severity ordering for safety floor enforcement
RISK_SEVERITY = {
    "NORMAL": 0,
    "CONCERNING": 1,
    "HIGH_CONCERN": 2,
    "IMMEDIATE_SAFETY": 3,
}


def _resolve_final_risk_level(rule_level: str, llm_proposed_level: str) -> str:
    """
    SAFETY-CRITICAL: Computes the final risk level.

    Rule: final = max(rule_level, llm_proposed_level) by severity ordering.
    The rule engine (RiskClassifier) is the safety floor — it can only escalate,
    never downgrade the LLM's assessment. The LLM is the primary signal for nuanced
    risk detection when the rule engine returns NORMAL or CONCERNING.

    Examples:
      rule=NORMAL,       llm=HIGH_CONCERN  -> HIGH_CONCERN  (LLM's deeper analysis wins)
      rule=HIGH_CONCERN, llm=NORMAL        -> HIGH_CONCERN  (safety floor wins, no downgrade)
      rule=IMMEDIATE_SAFETY, llm=NORMAL    -> IMMEDIATE_SAFETY (crisis keyword always wins)
    """
    rule_sev = RISK_SEVERITY.get(rule_level, 0)
    llm_sev = RISK_SEVERITY.get(llm_proposed_level, 0)
    return rule_level if rule_sev >= llm_sev else llm_proposed_level


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
    # ── 1. Resolve or create user ──────────────────────────────────────────
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

    # ── 2. Resolve or create profile ───────────────────────────────────────
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

    # ── 3. Resolve or create conversation ──────────────────────────────────
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

    # ── 4. Current scores & baselines ─────────────────────────────────────
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

    # ── 5. Pre-analyze user text signals ──────────────────────────────────
    analysis = WellbeingAnalyzer.analyze_message(req.message, current_scores)

    # ── 6. SAFETY FLOOR: Deterministic Risk Classification ────────────────
    # SAFETY-CRITICAL: This runs FIRST and its result is the mandatory floor.
    # It must NEVER be weakened, removed, or bypassed. See module docstring.
    rule_level, risk_reasons, safety_guidance = RiskClassifier.evaluate(
        text=req.message,
        dimension_scores=analysis["updated_scores"],
        score_deltas=analysis["score_deltas"]
    )

    # ── 7. Fetch recent conversation history for context ──────────────────
    past_messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at.asc()).all()
    history_formatted = [{"role": m.role, "content": m.content} for m in past_messages]

    # ── 8. LLM Generation (PRIMARY risk signal + patterns) ─────────────────
    # Pass db/user_id for tool-use (Task 4). If tool-use fails, falls back to
    # simple JSON generation, then to deterministic fallback.
    llm_output = LLMAgent.generate_response(
        user_message=req.message,
        conversation_history=history_formatted,
        current_scores=analysis["updated_scores"],
        active_patterns=[],  # Will be computed after LLM runs (Task 3 merge)
        risk_level=rule_level,
        safety_guidance=safety_guidance,
        db=db,
        user_id=str(user.id),
        conversation_id=str(conversation.id),
    )

    # ── 9. SAFETY FLOOR ENFORCEMENT (Tasks 2 & 4) ─────────────────────────
    # Extract LLM's proposed risk level from structured output.
    # SAFETY-CRITICAL: The rule engine can only escalate, never downgrade.
    # If the LLM proposes a HIGHER level than rules found, trust the LLM.
    # If the LLM proposes a LOWER level than rules found, the rules win.
    llm_risk_assessment = llm_output.get("risk_assessment", {})
    llm_proposed_level = llm_risk_assessment.get("proposed_level", "NORMAL")
    llm_risk_reasoning = llm_risk_assessment.get("reasoning", "")

    # Resolve final level using safety floor logic
    final_risk_level = _resolve_final_risk_level(rule_level, llm_proposed_level)

    # Re-fetch safety guidance if final level differs from rule engine's output
    if final_risk_level != rule_level:
        _, _, safety_guidance = RiskClassifier.evaluate(
            text=req.message,
            llm_suggested_risk=final_risk_level
        )

    # Build combined risk reasons (include LLM reasoning if it contributed)
    combined_reasons = list(risk_reasons)
    if llm_risk_reasoning and llm_proposed_level != "NORMAL":
        combined_reasons.append(f"[LLM Assessment] {llm_risk_reasoning}")

    # ── 10. ESCALATION TRIGGER (Task 1) ───────────────────────────────────
    # Runs right after final risk level is determined.
    # HIGH_CONCERN or IMMEDIATE_SAFETY always creates an Escalation audit record.
    # This is the integration point for EscalationService regardless of which
    # source (rules or LLM) drove the risk level.
    escalation_record = EscalationService.trigger(
        db=db,
        user_id=user.id,
        conversation_id=conversation.id,
        risk_level=final_risk_level,
        reason="; ".join(combined_reasons) if combined_reasons else f"Risk level {final_risk_level} triggered"
    )

    # ── 11. Pattern Detection with LLM observations (Task 3) ──────────────
    llm_pattern_observations = llm_output.get("pattern_observations", [])
    active_patterns_raw = PatternDetector.detect_patterns(
        current_scores=analysis["updated_scores"],
        baseline_scores=baseline_scores,
        signals=analysis["dimension_signals"],
        emotions=analysis["emotions"],
        llm_pattern_observations=llm_pattern_observations,
    )

    # ── 12. Update Profile & Persist Scores ───────────────────────────────
    profile.current_social = analysis["updated_scores"]["social"]
    profile.current_family = analysis["updated_scores"]["family"]
    profile.current_academic = analysis["updated_scores"]["academic"]
    profile.current_digital = analysis["updated_scores"]["digital"]
    profile.current_lifestyle = analysis["updated_scores"]["lifestyle"]
    profile.risk_level = final_risk_level
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
        risk_level_at_send=final_risk_level
    )
    db.add(user_msg_rec)

    # Save Assistant Message
    assistant_msg_rec = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=llm_output.get("response_text", ""),
        emotions_detected=[],
        dimension_signals={},
        risk_level_at_send=final_risk_level
    )
    db.add(assistant_msg_rec)

    # Save Patterns (merged rule-based + LLM)
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
                evidence_snippets=pat.get("evidence_snippets", []),
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
            risk_level_triggered=final_risk_level
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
        "risk_level": final_risk_level,
        "risk_reasons": combined_reasons,
        "risk_assessment": {
            "rule_level": rule_level,
            "llm_proposed_level": llm_proposed_level,
            "final_level": final_risk_level,
            "llm_reasoning": llm_risk_reasoning,
        },
        "safety_guidance": safety_guidance,
        "helplines": helplines if safety_guidance.get("show_helplines") else None,
        "active_patterns": active_patterns_raw,
        "intervention": created_intervention,
        "graph": graph_data,
        "escalation_triggered": escalation_record is not None,
        "escalation_id": str(escalation_record.id) if escalation_record else None,
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
