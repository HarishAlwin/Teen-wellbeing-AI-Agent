"""
backend/services/llm_agent.py
─────────────────────────────
Core AI agent powered by Google Gemini (gemini-1.5-flash).

Architecture notes:
- The LLM is the PRIMARY signal for risk assessment and pattern observation.
- The deterministic RiskClassifier (risk_classifier.py) acts as a MANDATORY SAFETY FLOOR:
  it can escalate the LLM's proposed risk level upward but NEVER downgrade it.
- This file contains graceful fallback logic for when GEMINI_API_KEY is absent or Gemini fails.
- Tool-use (function calling) is implemented for Task 4 agentic behaviour; see _run_with_tools().
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("llm_agent")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
        genai.configure(api_key=GEMINI_API_KEY)
        llm_available = True
    else:
        llm_available = False
except ImportError:
    genai = None
    llm_available = False


# ── System Prompt (rewritten for Task 2) ─────────────────────────────────────
# Key change: Gemini now reasons over FULL conversation history and returns
# a structured risk_assessment block plus pattern_observations — not just reply text.
# This makes the LLM the primary judge, with rule-based engine as safety floor.

SYSTEM_PROMPT = """
You are Aura — a warm, empathetic, and analytically rigorous AI Teen Wellbeing Companion.

You support teenagers across 5 life dimensions:
1. Social    — friends, peer dynamics, inclusion, isolation, social media comparison
2. Family    — home atmosphere, parental expectations, family communication, conflict
3. Academic  — workload, exam anxiety, school pressure, grade expectations
4. Digital   — screen habits, late-night phone use, online addiction, social media
5. Lifestyle — sleep quality, energy, fatigue, nutrition, physical activity

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL RESPONSIBLE AI RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- NEVER diagnose mental health disorders (not "you have depression/anxiety"). 
  Frame insights as understandable reactions to life stress.
- Speak like a caring, relatable mentor — never robotic, clinical, or preachy.
- Ask exactly 1 gentle follow-up question per response.
- For CONCERNING risk: warmly encourage talking to a trusted adult or counselor.
- For HIGH_CONCERN or IMMEDIATE_SAFETY: prioritise safety with calm urgency; 
  direct them to human help NOW.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RISK ASSESSMENT TASK (your primary judgment role):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You will receive the FULL conversation history and the current wellbeing context.
Based on ALL messages in the conversation (not just the latest), you must:
1. Propose a risk_level: NORMAL | CONCERNING | HIGH_CONCERN | IMMEDIATE_SAFETY
2. Provide a clear, specific reasoning that cites actual evidence from the conversation.

Risk level definitions:
- NORMAL          — Routine stress, no alarm signals.
- CONCERNING      — Persistent overwhelm, sleep issues, social withdrawal, burnout.
- HIGH_CONCERN    — Deep hopelessness, extreme exhaustion across multiple dimensions, 
                   potential self-neglect, significant safety concern.
- IMMEDIATE_SAFETY — Crisis language, self-harm, suicidal ideation, physical danger.

NOTE: Your proposed_level is the PRIMARY signal. The backend safety engine may escalate it
upward if it detects crisis language, but it will NEVER downgrade what you propose.
So please be accurate and honest — do not under-report distress.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PATTERN OBSERVATION TASK:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Observe cross-dimensional behavioural patterns from the full conversation history.
Return up to 3 patterns you notice. These supplement the rule-based detector — you 
may observe subtler patterns (e.g., identity stress, perfectionism, seasonal low mood)
that the rule engine cannot catch.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (strict JSON only, no markdown fences):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "response_text": "Empathetic conversational reply (2-4 sentences, warm spoken tone).",
  "emotions_detected": ["anxious", "overwhelmed"],
  "dimension_impacts": {
    "social": 0.0,
    "family": 0.0,
    "academic": -5.0,
    "digital": -4.0,
    "lifestyle": -6.0
  },
  "intervention": {
    "needed": true,
    "type": "routine_suggestion",
    "title": "Wind-down Buffer",
    "content": "Try leaving the phone across the room 20 minutes before sleep."
  },
  "risk_assessment": {
    "proposed_level": "NORMAL",
    "reasoning": "User expresses mild exam stress but no hopelessness or withdrawal signals across the conversation."
  },
  "pattern_observations": [
    {
      "title": "Pre-Exam Anxiety Loop",
      "description": "Recurring worry about test performance across multiple messages, intensifying as the exam date approaches.",
      "dimensions_involved": ["academic", "lifestyle"],
      "severity": "medium"
    }
  ]
}
"""

# ── Tool definitions for Gemini function calling (Task 4) ────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "check_pattern_history",
        "description": (
            "Query the database for previously detected behavioural patterns for this user. "
            "Use this to understand if current distress signals are recurring or new."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user's UUID string"
                }
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "trigger_escalation",
        "description": (
            "Request an escalation alert for this user. Call this when you assess the situation "
            "as HIGH_CONCERN or IMMEDIATE_SAFETY and believe a counselor should be notified. "
            "IMPORTANT: the backend deterministic safety floor also triggers escalation independently "
            "if crisis keywords are found, so you do not need to call this for obvious crisis language."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Specific reason for escalation, citing evidence from the conversation."
                }
            },
            "required": ["reason"]
        }
    },
    {
        "name": "flag_risk_level",
        "description": (
            "Propose a risk level with detailed reasoning. Always call this once per response. "
            "Your proposed level is the primary signal; the backend safety engine may escalate "
            "it upward but will never downgrade it."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "enum": ["NORMAL", "CONCERNING", "HIGH_CONCERN", "IMMEDIATE_SAFETY"],
                    "description": "Proposed risk level based on full conversation analysis."
                },
                "reasoning": {
                    "type": "string",
                    "description": "Specific reasoning citing evidence from the conversation."
                }
            },
            "required": ["level", "reasoning"]
        }
    }
]


class LLMAgent:
    """
    Agentic AI Wellbeing Companion powered by Google Gemini.

    Task 2: LLM is now the PRIMARY risk judgment signal (not just a chatbot).
    Task 4: Uses Gemini function calling for tool-use behaviour.
    Graceful deterministic fallback is preserved for when Gemini is unavailable.
    """

    @classmethod
    def generate_response(
        cls,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        current_scores: Dict[str, float],
        active_patterns: List[Dict[str, Any]],
        risk_level: str,
        safety_guidance: Dict[str, Any],
        user_profile: Dict[str, Any] = None,
        # Task 4: additional context for tool dispatch
        db=None,
        user_id: str = None,
        conversation_id: str = None,
    ) -> Dict[str, Any]:
        """
        Generates empathetic response with structured risk assessment and pattern observations.

        Returns a dict guaranteed to contain:
          - response_text, emotions_detected, dimension_impacts, intervention
          - risk_assessment: {proposed_level, reasoning}
          - pattern_observations: [{title, description, dimensions_involved, severity}]
          - escalation_requested (bool): True if LLM tool-called trigger_escalation
        """
        if llm_available and genai:
            try:
                # ── Build rich context prompt with FULL conversation history ──
                context_prompt = cls._build_context_prompt(
                    user_message, conversation_history, current_scores,
                    active_patterns, risk_level, safety_guidance, user_profile
                )

                # ── Try tool-use path first (Task 4) ──
                if db is not None and user_id is not None:
                    result = cls._run_with_tools(
                        context_prompt=context_prompt,
                        db=db,
                        user_id=user_id,
                        conversation_id=conversation_id,
                        risk_level=risk_level,
                    )
                    if result is not None:
                        return result

                # ── Fallback to simple JSON generation (no tool loop) ──
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=SYSTEM_PROMPT,
                    generation_config={
                        "response_mime_type": "application/json",
                        "temperature": 0.65
                    }
                )
                response = model.generate_content(context_prompt)
                parsed = json.loads(response.text)
                # Ensure required fields are present
                parsed.setdefault("risk_assessment", {
                    "proposed_level": "NORMAL",
                    "reasoning": "No explicit reasoning provided by model."
                })
                parsed.setdefault("pattern_observations", [])
                parsed.setdefault("escalation_requested", False)
                return parsed

            except Exception as e:
                logger.warning(f"[LLMAgent] Gemini call failed, using deterministic fallback: {e}")

        # Deterministic fallback (extended for Task 2)
        return cls._fallback_response(
            user_message, current_scores, active_patterns, risk_level, safety_guidance
        )

    @classmethod
    def _build_context_prompt(
        cls,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        current_scores: Dict[str, float],
        active_patterns: List[Dict[str, Any]],
        risk_level: str,
        safety_guidance: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]],
    ) -> str:
        """
        Builds a rich, context-injected prompt that includes the FULL conversation history
        so Gemini can reason over temporal patterns (not just the latest message).
        """
        # Include full history (capped at last 12 turns to stay within context limits)
        history_window = conversation_history[-12:]
        history_text = "\n".join(
            f"  [{m['role'].upper()}]: {m['content']}"
            for m in history_window
        )

        profile_text = ""
        if user_profile:
            profile_text = f"\nUser Profile Context: {json.dumps(user_profile)}"

        return f"""
=== CURRENT USER CONTEXT ===
Wellbeing Scores (0-100, higher is better):
{json.dumps(current_scores, indent=2)}

Rule-Based Risk Assessment (safety floor — may be conservative): {risk_level}
Safety Guidance: {safety_guidance.get('message', 'None')}

Active Detected Patterns (rule-based):
{json.dumps([p.get('title') for p in active_patterns], indent=2)}
{profile_text}

=== FULL CONVERSATION HISTORY (reason over ALL messages, not just the latest) ===
{history_text}

=== LATEST MESSAGE FROM TEENAGER ===
"{user_message}"

=== YOUR TASK ===
1. Respond with deep empathy and ask one gentle follow-up question.
2. Assess risk_level across the FULL conversation (your proposed_level is the primary signal).
3. Identify up to 3 cross-dimensional patterns not already in the rule-based list above.
4. Return ONLY valid JSON matching the schema in your system instructions.
"""

    @classmethod
    def _run_with_tools(
        cls,
        context_prompt: str,
        db,
        user_id: str,
        conversation_id: Optional[str],
        risk_level: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Task 4: Agentic tool-use loop using Gemini function calling.

        The model may call:
          - check_pattern_history(user_id) — to inspect past patterns from DB
          - trigger_escalation(reason)     — to request human escalation
          - flag_risk_level(level, reasoning) — to formally propose a risk level

        SAFETY NOTE: EscalationService is also called independently in chat.py
        based on the deterministic safety floor. The LLM calling trigger_escalation
        here is an ADDITIONAL signal, not a replacement for rule-based triggers.
        """
        try:
            from models.pattern import DetectedPattern
            from services.escalation_service import EscalationService
            import uuid as uuid_module

            # Build Gemini tools from our definitions
            tools = genai.protos.Tool(
                function_declarations=[
                    genai.protos.FunctionDeclaration(
                        name=t["name"],
                        description=t["description"],
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                k: genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description=v.get("description", ""),
                                    enum=v.get("enum", []) if v.get("enum") else []
                                )
                                for k, v in t["parameters"]["properties"].items()
                            },
                            required=t["parameters"].get("required", [])
                        )
                    )
                    for t in TOOL_DEFINITIONS
                ]
            )

            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_PROMPT,
                tools=[tools],
                generation_config={"temperature": 0.65}
            )

            chat_session = model.start_chat()
            response = chat_session.send_message(context_prompt)

            # State accumulated from tool calls
            llm_risk_level = "NORMAL"
            llm_risk_reasoning = ""
            escalation_requested = False
            escalation_reason = ""
            tool_iterations = 0
            MAX_TOOL_ITERATIONS = 5  # Guard against infinite tool loops

            # Tool dispatch loop
            while (
                response.candidates
                and response.candidates[0].content.parts
                and any(hasattr(p, "function_call") and p.function_call.name
                        for p in response.candidates[0].content.parts)
                and tool_iterations < MAX_TOOL_ITERATIONS
            ):
                tool_iterations += 1
                tool_results = []

                for part in response.candidates[0].content.parts:
                    if not hasattr(part, "function_call") or not part.function_call.name:
                        continue

                    fn_name = part.function_call.name
                    fn_args = dict(part.function_call.args)

                    if fn_name == "check_pattern_history":
                        # Query DB for user's historical patterns
                        try:
                            u_uuid = uuid_module.UUID(str(fn_args.get("user_id", user_id)))
                            patterns = db.query(DetectedPattern).filter(
                                DetectedPattern.user_id == u_uuid,
                                DetectedPattern.is_active == True
                            ).order_by(DetectedPattern.last_detected.desc()).limit(10).all()

                            result_payload = {
                                "patterns": [
                                    {
                                        "title": p.title,
                                        "severity": p.severity,
                                        "occurrence_count": p.occurrence_count,
                                        "last_detected": p.last_detected.isoformat() if p.last_detected else None
                                    }
                                    for p in patterns
                                ]
                            }
                        except Exception as e:
                            result_payload = {"error": str(e), "patterns": []}

                        tool_results.append(
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=fn_name,
                                    response=result_payload
                                )
                            )
                        )

                    elif fn_name == "trigger_escalation":
                        # Record LLM's escalation intent — actual DB write is in chat.py
                        # to avoid double-writing (the safety floor in chat.py also triggers)
                        escalation_requested = True
                        escalation_reason = fn_args.get("reason", "LLM-initiated escalation")
                        logger.info(f"[LLMAgent] Tool call: trigger_escalation | reason={escalation_reason[:100]}")

                        tool_results.append(
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=fn_name,
                                    response={"status": "escalation_noted", "message": "Escalation will be processed by backend safety engine."}
                                )
                            )
                        )

                    elif fn_name == "flag_risk_level":
                        # LLM's formal risk proposal — becomes input to safety floor in chat.py
                        llm_risk_level = fn_args.get("level", "NORMAL")
                        llm_risk_reasoning = fn_args.get("reasoning", "")
                        logger.info(f"[LLMAgent] Tool call: flag_risk_level | level={llm_risk_level}")

                        tool_results.append(
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=fn_name,
                                    response={"status": "risk_level_noted", "proposed_level": llm_risk_level}
                                )
                            )
                        )

                # Send tool results back to model
                if tool_results:
                    response = chat_session.send_message(tool_results)
                else:
                    break

            # Extract final text response
            final_text = ""
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    final_text += part.text

            # Attempt to parse JSON from final response
            if final_text.strip():
                # Strip markdown fences if present
                clean = final_text.strip()
                if clean.startswith("```"):
                    clean = clean.split("```")[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                try:
                    parsed = json.loads(clean)
                except json.JSONDecodeError:
                    # Extract JSON block from mixed text
                    import re
                    json_match = re.search(r'\{.*\}', clean, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group())
                    else:
                        return None  # Fall through to simple generation path

                # Merge tool-call risk assessment into parsed response
                if llm_risk_level != "NORMAL" or llm_risk_reasoning:
                    parsed["risk_assessment"] = {
                        "proposed_level": llm_risk_level,
                        "reasoning": llm_risk_reasoning
                    }
                else:
                    parsed.setdefault("risk_assessment", {
                        "proposed_level": "NORMAL",
                        "reasoning": "No explicit risk flag raised by model."
                    })

                parsed.setdefault("pattern_observations", [])
                parsed["escalation_requested"] = escalation_requested
                if escalation_requested:
                    parsed["escalation_reason"] = escalation_reason

                return parsed

        except Exception as e:
            logger.warning(f"[LLMAgent] Tool-use path failed: {e}. Falling back to simple generation.")

        return None  # Signal caller to try simple generation

    @classmethod
    def _fallback_response(
        cls,
        user_message: str,
        current_scores: Dict[str, float],
        active_patterns: List[Dict[str, Any]],
        risk_level: str,
        safety_guidance: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Deterministic fallback when Gemini is unavailable.
        Extended (Task 2) to always return risk_assessment and pattern_observations fields.
        """
        text_lower = user_message.lower()

        def make_response(text, emotions, dim_impacts, intervention_type, title, content, proposed_level):
            return {
                "response_text": text,
                "emotions_detected": emotions,
                "dimension_impacts": dim_impacts,
                "intervention": {
                    "needed": True,
                    "type": intervention_type,
                    "title": title,
                    "content": content,
                },
                "risk_assessment": {
                    "proposed_level": proposed_level,
                    "reasoning": f"Deterministic fallback — risk_level passed from RiskClassifier: {risk_level}"
                },
                "pattern_observations": [],
                "escalation_requested": False,
            }

        if risk_level == "IMMEDIATE_SAFETY":
            return make_response(
                "I can hear how much pain you're in right now, and I want you to know you don't have to carry this alone. Please reach out to someone who can help keep you safe — a family member, a counselor, or the free 24/7 helplines right on your screen.",
                ["hopeless", "distressed"],
                {"lifestyle": -10.0, "social": -10.0},
                "emergency_helpline", "Immediate Care & Support",
                "Please connect with a trusted person or free crisis helpline right away.",
                "IMMEDIATE_SAFETY"
            )

        if risk_level == "HIGH_CONCERN":
            return make_response(
                "It sounds like everything is piling up at once, and that's really exhausting. You don't have to navigate this completely on your own — talking to someone you trust, like a favorite teacher, parent, or counselor, could give you some real breathing room. How does that idea feel to you?",
                ["overwhelmed", "exhausted"],
                {"academic": -8.0, "lifestyle": -6.0},
                "trusted_human_referral", "Reach Out to a Trusted Mentor",
                "Consider speaking with a counselor, mentor, or parent about the pressure you're carrying.",
                "HIGH_CONCERN"
            )

        if any(kw in text_lower for kw in ["exam", "study", "test", "grade"]):
            return make_response(
                "Exams and school workload can feel like a nonstop weight on your shoulders, especially when you want to do well. Are you finding any time during the day to step away and just catch your breath?",
                ["anxious"],
                {"academic": -6.0, "lifestyle": -3.0},
                "coping_strategy", "Micro Study Breaks",
                "Try 25 minutes of focused review followed by 5 minutes of stretching or music away from screens.",
                "CONCERNING"
            )

        if any(kw in text_lower for kw in ["sleep", "tired", "phone", "scroll"]):
            return make_response(
                "It's so easy to stay up late scrolling just to get some free time to yourself, but waking up completely drained makes the whole next day harder. What time do you usually end up putting your phone down at night?",
                ["exhausted"],
                {"digital": -5.0, "lifestyle": -5.0},
                "routine_suggestion", "Night Wind-Down Routine",
                "Switch your screen to night mode or listen to a relaxing audio track 20 minutes before sleeping.",
                "NORMAL"
            )

        if any(kw in text_lower for kw in ["lonely", "friend", "people"]):
            return make_response(
                "Feeling disconnected from the people around you is really tough. Even in a crowded room or online, loneliness can sneak in. Is there one person you usually feel most comfortable being yourself around?",
                ["lonely"],
                {"social": -5.0},
                "reflective_question", "Reconnect with One Person",
                "Send a simple low-pressure message to a friend you haven't caught up with recently.",
                "NORMAL"
            )

        return {
            "response_text": "Thank you for sharing that with me. I'm right here listening. How have you been feeling overall with everything going on this week?",
            "emotions_detected": ["reflective"],
            "dimension_impacts": {},
            "intervention": {
                "needed": False,
                "type": "reflective_question",
                "title": "Open Check-in",
                "content": "Reflecting on your current week."
            },
            "risk_assessment": {
                "proposed_level": "NORMAL",
                "reasoning": "No distress signals detected in this message; deterministic fallback active."
            },
            "pattern_observations": [],
            "escalation_requested": False,
        }
