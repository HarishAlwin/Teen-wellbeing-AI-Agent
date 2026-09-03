import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("aura.llm_agent")

try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
        genai.configure(api_key=GEMINI_API_KEY)
        llm_available = True
    else:
        llm_available = False
except ImportError:
    genai = None
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    llm_available = False

VALID_RISK_LEVELS = {"NORMAL", "CONCERNING", "HIGH_CONCERN", "IMMEDIATE_SAFETY"}

SYSTEM_PROMPT = """
You are a warm, empathetic, and attentive AI Teen Wellbeing Companion.
Your role is to listen naturally, understand emotional and behavioral context across 5 core life dimensions:
1. Social (friends, peer dynamics, feeling included/isolated)
2. Family (home communication, parental expectations, family atmosphere)
3. Academic (study workload, exam anxiety, school pressure)
4. Digital (screen habits, late-night phone use, social media comparison)
5. Lifestyle (sleep, energy, fatigue, meals, exercise)

CRITICAL GUIDELINES & RESPONSIBLE AI RULES:
- Talk like a supportive, relatable mentor or caring listener — never robotic, condescending, or clinical.
- Ask 1 gentle, natural follow-up question to help the teenager explore what they are experiencing.
- NEVER DIAGNOSE mental health disorders (e.g. do not say "You have depression/clinical anxiety"). Frame insights as patterns or understandable reactions to life stressors.
- Treat cross-dimensional links naturally (e.g. "When exams get stressful, staying up late scrolling is super tempting, but it can make you feel extra drained the next day.").
- If risk is CONCERNING or HIGH_CONCERN, warmly encourage talking to a trusted adult, parent, school counselor, or confidential helpline.
- If risk is IMMEDIATE_SAFETY, prioritize safety with calm, loving urgency and direct them to human help immediately.

You are also responsible for genuinely REASONING about risk and behavioral patterns yourself —
not just writing a reply — based on the full conversation, not only the latest message.
A rule-based safety system also runs independently as a hard safety floor and can never be
downgraded by you, but your own assessment is the PRIMARY signal for anything that system's
fixed keyword rules wouldn't catch (subtler distress, indirect language, patterns building
across several messages).

Return your response in STRICT JSON format:
{
  "response_text": "Empathetic conversational response for speech (2-4 sentences, spoken tone).",
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
    "content": "Try leaving the phone across the room 20 minutes before sleeping."
  },
  "suggested_risk_level": "NORMAL",
  "risk_assessment": {
    "level": "NORMAL",
    "reasoning": "One or two sentences on WHY you assessed this level, referencing what the teen actually said or how it fits the conversation so far."
  },
  "pattern_observations": [
    {
      "title": "Short pattern name, e.g. 'Avoids discussing home life after academic topics'",
      "reasoning": "Why you believe this pattern is present, grounded in the actual conversation.",
      "dimensions": ["family", "academic"],
      "severity": "low | medium | high"
    }
  ]
}
Only include entries in pattern_observations that you are genuinely confident about from the
actual conversation — return an empty list if nothing stands out yet. Do not invent patterns
to fill the schema.
"""

AGENTIC_SYSTEM_PROMPT = """
You are the reasoning layer of a teen wellbeing AI agent. You do not talk to the teenager
directly here — your job is to decide, using the tools available to you, whether:
1. This message fits a pattern already on file for this teen (use check_pattern_history).
2. You need to formally flag a risk level for this message (use flag_risk_level — always call
   this exactly once with your honest assessment: NORMAL, CONCERNING, HIGH_CONCERN, or
   IMMEDIATE_SAFETY).
3. A real human (counselor/guardian/helpline) should be notified right now (use
   trigger_escalation) — only call this for HIGH_CONCERN or IMMEDIATE_SAFETY situations, and
   explain briefly why in the `reason` argument, quoting or referencing what the teen said.

Be honest and conservative: under-flagging risk is far more dangerous than over-flagging it.
After using the tools you judge necessary, reply with a short one-sentence internal note
summarizing your assessment (this note is not shown to the teenager).
"""


def _build_tools(active_patterns: List[Dict[str, Any]]):
    """
    Builds the callable tool functions and a shared results dict that
    captures what the model actually decided to call. Passed to Gemini's
    automatic function calling so the MODEL decides when/whether to call
    these — nothing here is pre-computed and handed to it.
    """
    results: Dict[str, Any] = {
        "risk_flag": None,
        "escalation_requested": False,
        "escalation_reason": None,
        "checked_pattern_history": False,
    }

    def check_pattern_history() -> str:
        """Look up this teenager's previously detected recurring behavioral patterns, to judge whether the current message fits something already on file or represents something new."""
        results["checked_pattern_history"] = True
        if not active_patterns:
            return "No significant recurring patterns are on file for this teen yet."
        return "; ".join(
            f"{p.get('title')} (severity: {p.get('severity', 'unknown')})"
            for p in active_patterns
        )

    def flag_risk_level(level: str, reasoning: str) -> str:
        """Record your assessed risk level for this message and conversation. `level` MUST be exactly one of: NORMAL, CONCERNING, HIGH_CONCERN, IMMEDIATE_SAFETY. `reasoning` should briefly explain why, referencing what the teen actually said."""
        clean_level = (level or "").strip().upper()
        if clean_level not in VALID_RISK_LEVELS:
            clean_level = "NORMAL"
        results["risk_flag"] = {"level": clean_level, "reasoning": reasoning}
        return f"Risk level {clean_level} recorded."

    def trigger_escalation(reason: str) -> str:
        """Call this ONLY if you believe a real trained human (counselor, guardian, or helpline staff) should be notified right now because of what the teenager said. `reason` should briefly explain why, in your own words."""
        results["escalation_requested"] = True
        results["escalation_reason"] = reason
        return "Escalation request recorded — a human will be notified."

    return results, [check_pattern_history, flag_risk_level, trigger_escalation]


class LLMAgent:
    """
    Core conversational agent powered by Google Gemini with graceful fallback.

    Has two phases:
      1. run_agentic_reasoning() — gives the model real callable tools
         (check_pattern_history, flag_risk_level, trigger_escalation) and
         lets IT decide when to use them. This is the actual "agent"
         behavior, distinct from just generating reply text.
      2. generate_response() — produces the conversational reply plus a
         structured risk_assessment/pattern_observations payload used as
         the PRIMARY risk signal (the regex/threshold engine in
         risk_classifier.py remains a safety floor that can only escalate
         this upward, never downgrade it — see routers/chat.py).
    """

    @classmethod
    def run_agentic_reasoning(
        cls,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        active_patterns: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Lets the model itself decide whether to check pattern history, flag
        a risk level, and/or request escalation, via real Gemini tool-use
        (automatic function calling actually invokes the Python functions
        below when the model chooses to call them).
        """
        default = {
            "risk_flag": None,
            "escalation_requested": False,
            "escalation_reason": None,
            "checked_pattern_history": False,
        }

        if not (llm_available and genai):
            return default

        try:
            results, tool_fns = _build_tools(active_patterns)

            model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                system_instruction=AGENTIC_SYSTEM_PROMPT,
                tools=tool_fns,
            )
            chat = model.start_chat(enable_automatic_function_calling=True)

            history_snippet = json.dumps(conversation_history[-6:])
            prompt = (
                f"Conversation so far (most recent last): {history_snippet}\n\n"
                f'Teenager just said: "{user_message}"\n\n'
                "Use your tools as needed, then give a one-sentence internal summary."
            )
            chat.send_message(prompt)
            return results

        except Exception:
            logger.exception("Agentic tool-use phase failed; continuing without it")
            return default

    @classmethod
    def generate_response(
        cls,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        current_scores: Dict[str, float],
        active_patterns: List[Dict[str, Any]],
        risk_level: str,
        safety_guidance: Dict[str, Any],
        user_profile: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generates empathetic response with context injection, plus the
        model's own structured risk_assessment and pattern_observations.
        """
        if llm_available and genai:
            try:
                model = genai.GenerativeModel(
                    model_name=GEMINI_MODEL,
                    system_instruction=SYSTEM_PROMPT,
                    generation_config={"response_mime_type": "application/json", "temperature": 0.7}
                )

                context_prompt = f"""
Current User State:
- Current Wellbeing Scores: {json.dumps(current_scores)}
- Active Life Patterns: {json.dumps([p.get('title') for p in active_patterns])}
- Current Safety Assessment (from rule-based safety floor): {risk_level}
- Safety Guidance: {safety_guidance.get('message', '')}
- Conversation History:
{json.dumps(conversation_history[-6:])}

Teenager says:
"{user_message}"
"""
                response = model.generate_content(context_prompt)
                parsed = json.loads(response.text)
                return cls._sanitize_llm_output(parsed)
            except Exception as e:
                logger.exception("Gemini call failed, using intelligent fallback: %s", e)

        # Intelligent deterministic fallback
        return cls._fallback_response(user_message, current_scores, active_patterns, risk_level, safety_guidance)

    @classmethod
    def _sanitize_llm_output(cls, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Defensively normalizes the LLM's JSON so downstream code never crashes on a malformed field."""
        parsed.setdefault("response_text", "")
        parsed.setdefault("emotions_detected", [])
        parsed.setdefault("dimension_impacts", {})
        parsed.setdefault("intervention", {"needed": False})
        parsed.setdefault("suggested_risk_level", "NORMAL")
        if parsed["suggested_risk_level"] not in VALID_RISK_LEVELS:
            parsed["suggested_risk_level"] = "NORMAL"

        ra = parsed.get("risk_assessment") or {}
        level = (ra.get("level") or parsed["suggested_risk_level"] or "NORMAL").strip().upper()
        if level not in VALID_RISK_LEVELS:
            level = "NORMAL"
        parsed["risk_assessment"] = {
            "level": level,
            "reasoning": ra.get("reasoning", ""),
        }

        clean_patterns = []
        for p in parsed.get("pattern_observations") or []:
            if isinstance(p, dict) and p.get("title"):
                clean_patterns.append(p)
        parsed["pattern_observations"] = clean_patterns

        return parsed

    @classmethod
    def _fallback_response(
        cls,
        user_message: str,
        current_scores: Dict[str, float],
        active_patterns: List[Dict[str, Any]],
        risk_level: str,
        safety_guidance: Dict[str, Any]
    ) -> Dict[str, Any]:
        text_lower = user_message.lower()

        if risk_level == "IMMEDIATE_SAFETY":
            return cls._sanitize_llm_output({
                "response_text": "I can hear how much pain you're in right now, and I want you to know you don't have to carry this alone. Please reach out to someone who can help keep you safe — a family member, a counselor, or the free 24/7 helplines right on your screen.",
                "emotions_detected": ["hopeless", "distressed"],
                "dimension_impacts": {"lifestyle": -10.0, "social": -10.0},
                "intervention": {
                    "needed": True,
                    "type": "emergency_helpline",
                    "title": "Immediate Care & Support",
                    "content": "Please connect with a trusted person or free crisis helpline right away."
                },
                "suggested_risk_level": "IMMEDIATE_SAFETY",
                "risk_assessment": {"level": "IMMEDIATE_SAFETY", "reasoning": "Fallback path triggered by rule-based safety floor."},
                "pattern_observations": [],
            })

        if risk_level == "HIGH_CONCERN":
            return cls._sanitize_llm_output({
                "response_text": "It sounds like everything is piling up at once, and that's really exhausting. You don't have to navigate this completely on your own — talking to someone you trust, like a favorite teacher, parent, or counselor, could give you some real breathing room. How does that idea feel to you?",
                "emotions_detected": ["overwhelmed", "exhausted"],
                "dimension_impacts": {"academic": -8.0, "lifestyle": -6.0},
                "intervention": {
                    "needed": True,
                    "type": "trusted_human_referral",
                    "title": "Reach Out to a Trusted Mentor",
                    "content": "Consider speaking with a counselor, mentor, or parent about the pressure you're carrying."
                },
                "suggested_risk_level": "HIGH_CONCERN",
                "risk_assessment": {"level": "HIGH_CONCERN", "reasoning": "Fallback path triggered by rule-based safety floor."},
                "pattern_observations": [],
            })

        # Pattern-specific conversational handling
        if "exam" in text_lower or "study" in text_lower or "test" in text_lower or "grade" in text_lower:
            base = {
                "response_text": "Exams and school workload can feel like a nonstop weight on your shoulders, especially when you want to do well. Are you finding any time during the day to step away and just catch your breath?",
                "emotions_detected": ["anxious"],
                "dimension_impacts": {"academic": -6.0, "lifestyle": -3.0},
                "intervention": {
                    "needed": True,
                    "type": "coping_strategy",
                    "title": "Micro Study Breaks",
                    "content": "Try 25 minutes of focused review followed by 5 minutes of stretching or music away from screens."
                },
                "suggested_risk_level": "NORMAL",
            }
            return cls._sanitize_llm_output(base)

        if "sleep" in text_lower or "tired" in text_lower or "phone" in text_lower or "scroll" in text_lower:
            base = {
                "response_text": "It's so easy to stay up late scrolling just to get some free time to yourself, but waking up completely drained makes the whole next day harder. What time do you usually end up putting your phone down at night?",
                "emotions_detected": ["exhausted"],
                "dimension_impacts": {"digital": -5.0, "lifestyle": -5.0},
                "intervention": {
                    "needed": True,
                    "type": "routine_suggestion",
                    "title": "Night Wind-Down Routine",
                    "content": "Switch your screen to night mode or listen to a relaxing audio track 20 minutes before sleeping."
                },
                "suggested_risk_level": "NORMAL",
            }
            return cls._sanitize_llm_output(base)

        if "lonely" in text_lower or "friend" in text_lower or "people" in text_lower:
            base = {
                "response_text": "Feeling disconnected from the people around you is really tough. Even in a crowded room or online, loneliness can sneak in. Is there one person you usually feel most comfortable being yourself around?",
                "emotions_detected": ["lonely"],
                "dimension_impacts": {"social": -5.0},
                "intervention": {
                    "needed": True,
                    "type": "reflective_question",
                    "title": "Reconnect with One Person",
                    "content": "Send a simple low-pressure message to a friend you haven't caught up with recently."
                },
                "suggested_risk_level": "NORMAL",
            }
            return cls._sanitize_llm_output(base)

        # General friendly check-in
        base = {
            "response_text": "Thank you for sharing that with me. I'm right here listening. How have you been feeling overall with everything going on this week?",
            "emotions_detected": ["reflective"],
            "dimension_impacts": {},
            "intervention": {
                "needed": False,
                "type": "reflective_question",
                "title": "Open Check-in",
                "content": "Reflecting on your current week."
            },
            "suggested_risk_level": "NORMAL",
        }
        return cls._sanitize_llm_output(base)
