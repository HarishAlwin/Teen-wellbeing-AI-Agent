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

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import re
import asyncio

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
from services.wellbeing_state_cache import get_cached_state
from services.emergency_dispatcher import EmergencyDispatcher
from jobs.specialist_job import run_specialist_job
from auth import get_current_user

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
    # NOTE: user_id is intentionally REMOVED — it is now derived from the
    # authenticated session (JWT token) to prevent impersonation.
    conversation_id: Optional[str] = None
    message: str
    country_code: Optional[str] = "IN"

class FeedbackRequest(BaseModel):
    intervention_id: Optional[str] = None
    rating: str  # helpful | somewhat_helpful | not_helpful
    comment: Optional[str] = None


@router.get("")
@router.head("")
def chat_health_check():
    return {"status": "ok", "service": "chat"}


@router.post("")
async def send_message(
    req: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # ── 1. Use authenticated user (impersonation gap closed) ───────────────────
    user = current_user

    # ── 2. Resolve or create profile ───────────────────────────────────────────
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

    # ── 3. Resolve or create conversation ──────────────────────────────────────
    conversation = None
    if req.conversation_id:
        try:
            c_uuid = uuid.UUID(req.conversation_id)
            conversation = db.query(Conversation).filter(Conversation.id == c_uuid).first()
            # Safety: ensure the conversation belongs to this user
            if conversation and conversation.user_id != user.id:
                conversation = None
        except ValueError:
            pass

    if not conversation:
        conversation = Conversation(user_id=user.id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # ── 4. Current scores & baselines ─────────────────────────────────────────
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

    # ── 5. Pre-analyze user text signals ──────────────────────────────────────
    analysis = WellbeingAnalyzer.analyze_message(req.message, current_scores)

    # ── 6. SAFETY FLOOR: Deterministic Risk Classification ────────────────────
    # SAFETY-CRITICAL: This runs FIRST and its result is the mandatory floor.
    # It must NEVER be weakened, removed, or bypassed. See module docstring.
    rule_level, risk_reasons, safety_guidance = RiskClassifier.evaluate(
        text=req.message,
        dimension_scores=analysis["updated_scores"],
        score_deltas=analysis["score_deltas"]
    )

    # ── 7. Fetch recent conversation history for context ──────────────────────
    past_messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at.asc()).all()
    history_formatted = [{"role": m.role, "content": m.content} for m in past_messages]

    # ── 7b. Read wellbeing state cache (fast path — no specialist calls here) ──
    # If the background job has run for this user, inject its specialist insights
    # into the LLM context. If not (first message or job pending), cache is None
    # and behaviour is identical to the pre-upgrade flow.
    wellbeing_cache = get_cached_state(db, user.id)

    # ── 8. LLM Generation (PRIMARY risk signal + patterns) ─────────────────────
    # Pass db/user_id for tool-use. Passes RoBERTa sentiment & GoEmotions to Groq.
    llm_output = LLMAgent.generate_response(
        user_message=req.message,
        conversation_history=history_formatted,
        current_scores=analysis["updated_scores"],
        active_patterns=[],  # Will be computed after LLM runs
        risk_level=rule_level,
        safety_guidance=safety_guidance,
        nlp_signals={
            "sentiment": analysis.get("sentiment"),
            "emotions": analysis.get("emotions")
        },
        wellbeing_state_cache=wellbeing_cache,
        db=db,
        user_id=str(user.id),
        conversation_id=str(conversation.id),
    )

    # ── 9. SAFETY FLOOR ENFORCEMENT (Tasks 2 & 4) ─────────────────────────────
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

    # ── 10. ESCALATION TRIGGER (Task 1) ───────────────────────────────────────
    # Runs right after final risk level is determined.
    # HIGH_CONCERN or IMMEDIATE_SAFETY always creates an Escalation audit record.
    # This is the integration point for EscalationService regardless of which
    # source (rules or LLM) drove the risk level.
    escalation_record = EscalationService.trigger(
        db=db,
        user_id=user.id,
        conversation_id=conversation.id,
        risk_level=final_risk_level,
        reason="; ".join(combined_reasons) if combined_reasons else f"Risk level {final_risk_level} triggered",
        user_message=req.message,
    )

    # Check for explicit user request to call/inform guardian or emergency contact
    call_command_detected = bool(re.search(r"\b(call|inform|alert|ring|dial|phone)\b.*(guardian|parent|emergency|helpline|counselor|\+?\d{10,12})", req.message.lower()))
    if call_command_detected and final_risk_level != "IMMEDIATE_SAFETY":
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                loop.create_task(
                    EmergencyDispatcher.dispatch(
                        user_id=str(user.id),
                        user_message=req.message,
                        risk_level="EXPLICIT_CALL_REQUEST",
                        reason="User requested direct call dispatch to guardian/contact."
                    )
                )
            else:
                asyncio.run(
                    EmergencyDispatcher.dispatch(
                        user_id=str(user.id),
                        user_message=req.message,
                        risk_level="EXPLICIT_CALL_REQUEST",
                        reason="User requested direct call dispatch to guardian/contact."
                    )
                )
        except Exception as e:
            pass

    # ── 11. Pattern Detection with LLM observations (Task 3) ──────────────────
    llm_pattern_observations = llm_output.get("pattern_observations", [])
    active_patterns_raw = PatternDetector.detect_patterns(
        current_scores=analysis["updated_scores"],
        baseline_scores=baseline_scores,
        signals=analysis["dimension_signals"],
        emotions=analysis["emotions"],
        llm_pattern_observations=llm_pattern_observations,
    )

    # ── 12. Update Profile & Persist Scores ───────────────────────────────────
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

    # ── 13. Fire async background specialist job (P1 fast/slow split) ──────────
    # This runs AFTER the response is committed and returned to the client.
    # It enriches the wellbeing state cache for the NEXT turn's LLM context.
    # If this fails, the current response is already returned — no UX impact.
    background_tasks.add_task(
        run_specialist_job,
        user_id=user.id,
        dimension_signals=analysis["dimension_signals"],
        user_message=req.message,
        active_patterns=active_patterns_raw,
        conversation_snippet=history_formatted[-3:] if history_formatted else None,
    )

    helplines = RiskClassifier.get_helpline_info(user.country_code or "IN")

    return {
        "user_id": str(user.id),
        "conversation_id": str(conversation.id),
        "response_text": llm_output.get("response_text", ""),
        "emotions_detected": analysis["emotions"],
        "detailed_emotions": analysis.get("detailed_emotions", []),
        "sentiment": analysis.get("sentiment", {}),
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
        "emergency_dispatch": {
            "dispatched": final_risk_level == "IMMEDIATE_SAFETY" or call_command_detected,
            "target": EmergencyDispatcher.format_phone_number(EmergencyDispatcher.EMERGENCY_DISPATCH_PHONE_NUMBER) or "Designated Guardian",
            "message_relayed": req.message,
            "status": "dispatched" if (final_risk_level == "IMMEDIATE_SAFETY" or call_command_detected) else "standby"
        }
    }


@router.post("/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    i_uuid = None
    if req.intervention_id:
        try:
            i_uuid = uuid.UUID(req.intervention_id)
        except ValueError:
            pass

    fb = Feedback(
        user_id=current_user.id,
        intervention_id=i_uuid,
        rating=req.rating,
        comment=req.comment
    )
    db.add(fb)

    # Update user preferences in profile
    profile = db.query(WellbeingProfile).filter(WellbeingProfile.user_id == current_user.id).first()
    if profile:
        prefs = dict(profile.preferences or {})
        prefs[f"feedback_rating_{req.rating}"] = prefs.get(f"feedback_rating_{req.rating}", 0) + 1
        profile.preferences = prefs



