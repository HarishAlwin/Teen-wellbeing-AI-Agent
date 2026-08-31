"""
backend/services/llm_agent.py
─────────────────────────────
Core AI agent powered by Groq API (llama-3.3-70b-versatile).

Architecture notes:
- The LLM is the PRIMARY signal for risk assessment and pattern observation.
- The deterministic RiskClassifier (risk_classifier.py) acts as a MANDATORY SAFETY FLOOR:
  it can escalate the LLM's proposed risk level upward but NEVER downgrade it.
- Uses Groq for ultra-low-latency (<250ms), human-like, empathetic reasoning.
- Tool-use (function calling) is implemented for agentic behaviour; see _run_with_tools().
- Graceful deterministic fallback is preserved for offline or when GROQ_API_KEY is absent.
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

# Groq Client Initialization
GROQ_MODEL = os.getenv("GROQ_MODEL", "groq/compound")
FALLBACK_MODELS = ["groq/compound", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "groq/compound-mini"]

groq_client = None
llm_available = False

try:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    if GROQ_API_KEY and GROQ_API_KEY != "your_groq_api_key_here":
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
        llm_available = True
        logger.info(f"[LLMAgent] Groq client initialized with model: {GROQ_MODEL}")
    else:
        logger.warning("[LLMAgent] GROQ_API_KEY not set. Using deterministic fallback.")
except Exception as e:
    logger.error(f"[LLMAgent] Could not initialize Groq client: {e}", exc_info=True)
    groq_client = None
    llm_available = False



# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are Jarvis / Aura — a warm, empathetic, and relatable AI Teen Wellbeing Companion.

You support teenagers across 5 core life dimensions:
1. Social    — friends, relationships, peer dynamics, inclusion, social anxiety
2. Family    — home atmosphere, parental expectations, family communication
3. Academic  — workload, exam anxiety, school pressure, future plans
4. Digital   — screen habits, late-night phone use, social media fatigue
5. Lifestyle — sleep quality, energy, fatigue, nutrition, physical activity

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL CONVERSATIONAL & SAFETY RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Act like a real, caring friend/mentor. Speak naturally, warmly, and concisely (2-3 sentences).
- Match the user's topic directly. If they talk about a breakup, school, or food, engage with that topic!
- NEVER diagnose disorders (no clinical jargon like "you have clinical depression").
- DO NOT panic or push crisis hotlines for routine vents (e.g., breakups, exam stress, feeling sad, casual chat). 
- For IMMEDIATE_SAFETY (explicit suicidal ideation, self-harm, or severe danger): An automated emergency dispatch call and SMS is automatically placed by the system to their emergency guardian contact sharing their situation. Acknowledge this with calm reassurance (e.g. "I'm right here with you. I've automatically alerted your designated emergency guardian so you don't have to carry this alone..."), keep them grounded, and stay present.
- For NORMAL and CONCERNING messages: listen attentively, validate their emotions, and ask 1 natural, gentle question. Do NOT mention emergency contacts or helplines.
- "intervention.needed" should be FALSE for most regular messages. Only set "needed": true if providing a concrete, gentle wellness micro-habit (like a 2-minute stretch or study break).


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RISK ASSESSMENT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- NORMAL          — Routine chat, casual vents, standard teenage challenges (breakups, tests, tiredness).
- CONCERNING      — Persistent overwhelm, deep stress, or recurring sadness across multiple messages.
- HIGH_CONCERN    — Explicit hopelessness, severe crisis, or indications of unsafe home abuse/danger.
- IMMEDIATE_SAFETY — Direct suicidal statements, active self-harm, or immediate physical emergency.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (strict valid JSON only):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "response_text": "Empathetic, natural conversational reply engaging directly with what they shared (2-3 sentences).",
  "emotions_detected": ["sadness"],
  "dimension_impacts": {
    "social": -2.0,
    "family": 0.0,
    "academic": 0.0,
    "digital": 0.0,
    "lifestyle": 0.0
  },
  "intervention": {
    "needed": false,
    "type": "reflective_question",
    "title": "Emotional Reflection",
    "content": "Take a moment to acknowledge your feelings."
  },
  "risk_assessment": {
    "proposed_level": "NORMAL",
    "reasoning": "User is discussing a breakup. Normal emotional reaction to relationship stress with no safety signals."
  },
  "pattern_observations": []
}
"""


# Tool definitions for Groq function calling
GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_pattern_history",
            "description": "Query database for previously detected behavioural patterns for this user.",
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
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_escalation",
            "description": "Request an escalation alert for this user when you assess HIGH_CONCERN or IMMEDIATE_SAFETY.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Specific reason citing evidence from conversation."
                    }
                },
                "required": ["reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "flag_risk_level",
            "description": "Propose a formal risk level with detailed reasoning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "string",
                        "enum": ["NORMAL", "CONCERNING", "HIGH_CONCERN", "IMMEDIATE_SAFETY"],
                        "description": "Proposed risk level."
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Evidence from conversation."
                    }
                },
                "required": ["level", "reasoning"]
            }
        }
    }
]


class LLMAgent:
    """
    Agentic AI Wellbeing Companion powered by Groq API.
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
        nlp_signals: Dict[str, Any] = None,
        wellbeing_state_cache: Optional[Dict[str, Any]] = None,
        db=None,
        user_id: str = None,
        conversation_id: str = None,
    ) -> Dict[str, Any]:
        """
        Generates empathetic response using Groq API with structured JSON output,
        grounded in RoBERTa Sentiment & GoEmotions signals.
        """
        global groq_client, llm_available

        # Check if Groq client can be lazily re-initialized if key was updated
        if not groq_client:
            current_key = os.getenv("GROQ_API_KEY", "")
            if current_key and current_key != "your_groq_api_key_here":
                try:
                    from groq import Groq
                    groq_client = Groq(api_key=current_key)
                    llm_available = True
                except Exception:
                    pass

        if llm_available and groq_client:
            models_to_try = [GROQ_MODEL] + [m for m in FALLBACK_MODELS if m != GROQ_MODEL]
            last_error = None

            for model_name in models_to_try:
                try:
                    # ── Build prompt messages ──
                    context_prompt = cls._build_context_prompt(
                        user_message, conversation_history, current_scores,
                        active_patterns, risk_level, safety_guidance, user_profile,
                        nlp_signals, wellbeing_state_cache
                    )

                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": context_prompt}
                    ]

                    # Call Groq Chat Completions with JSON Object Mode
                    response = groq_client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        response_format={"type": "json_object"},
                        temperature=0.6,
                        max_tokens=1024,
                    )

                    response_text = response.choices[0].message.content
                    parsed = json.loads(response_text)

                    parsed.setdefault("risk_assessment", {
                        "proposed_level": "NORMAL",
                        "reasoning": "No explicit risk flag raised by model."
                    })
                    parsed.setdefault("pattern_observations", [])
                    parsed.setdefault("escalation_requested", False)
                    return parsed

                except Exception as e:
                    last_error = e
                    logger.error(
                        f"[LLMAgent] Groq call failed on model '{model_name}': {type(e).__name__} - {e}",
                        exc_info=True
                    )

            if last_error:
                logger.error(f"[LLMAgent] All Groq models failed. Falling back to deterministic response.")

        # Deterministic fallback
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
        nlp_signals: Optional[Dict[str, Any]] = None,
        wellbeing_state_cache: Optional[Dict[str, Any]] = None,
    ) -> str:
        history_window = conversation_history[-12:]
        history_text = "\n".join(
            f"  [{m['role'].upper()}]: {m['content']}"
            for m in history_window
        )

        profile_text = ""
        if user_profile:
            profile_text = f"\nUser Profile Context: {json.dumps(user_profile)}"

        nlp_section = ""
        if nlp_signals:
            sentiment = nlp_signals.get("sentiment", {})
            emotions = nlp_signals.get("emotions", [])
            nlp_section = f"""
=== TRANSFORMER NLP ANALYSIS ===
Overall Sentiment Tone (cardiffnlp/twitter-roberta-base-sentiment-latest): {sentiment.get('label', 'unknown').upper()} (Confidence: {sentiment.get('score', 0):.2f})
Detected Emotions (SamLowe/roberta-base-go_emotions): {', '.join(emotions) if emotions else 'neutral'}
"""

        # ── Wellbeing State Cache (from async background specialist job) ────────
        # Injected when available — provides deeper dimension-level insights from
        # the PREVIOUS turn's specialist analysis. If None, this section is omitted
        # and behaviour is identical to the pre-upgrade fast path.
        cache_section = ""
        if wellbeing_state_cache:
            dims = wellbeing_state_cache.get("dimensions", {})
            cached_patterns = wellbeing_state_cache.get("patterns", [])
            job_ran_at = wellbeing_state_cache.get("job_ran_at", "unknown")
            cache_lines = []
            for dim, data in dims.items():
                insights = data.get("insights", [])
                flags = data.get("flags", [])
                delta = data.get("score_delta", 0.0)
                if insights or flags:
                    cache_lines.append(
                        f"  {dim.upper()}: delta={delta:+.1f}, flags={flags}, insights={insights}"
                    )
            cache_section = (
                "\n=== WELLBEING STATE CACHE (from prior specialist analysis) ===\n"
                + "\n".join(cache_lines)
                + f"\nCached patterns: {[p.get('title') for p in cached_patterns]}"
                + f"\n(Last updated: {job_ran_at})\n"
                if cache_lines else ""
            )

        return f"""
=== CURRENT USER CONTEXT ===
Wellbeing Scores (0-100, higher is better):
{json.dumps(current_scores, indent=2)}

Rule-Based Risk Assessment (safety floor): {risk_level}
Safety Guidance: {safety_guidance.get('message', 'None')}

Active Detected Patterns:
{json.dumps([p.get('title') for p in active_patterns], indent=2)}
{profile_text}
{nlp_section}{cache_section}
=== CONVERSATION HISTORY ===
{history_text}

=== LATEST MESSAGE FROM TEENAGER ===
"{user_message}"

=== YOUR TASK ===
1. Respond with deep empathy tailored to the detected emotional tone and ask one gentle follow-up question.
2. Assess risk_level across the FULL conversation.
3. Identify cross-dimensional patterns.
4. Return ONLY valid JSON matching the schema.
"""

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
        Deterministic fallback when Groq API is unavailable.
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
                    "reasoning": f"Deterministic safety fallback active (Risk: {risk_level})"
                },
                "pattern_observations": [],
                "escalation_requested": False,
            }

        if risk_level == "IMMEDIATE_SAFETY":
            return make_response(
                "I hear how much pain you're carrying right now, and you do not have to go through this alone. I've automatically placed a priority emergency alert and dispatch call to your designated emergency contact with what you shared so trusted support can reach you immediately. I'm staying right here with you.",
                ["hopeless", "distressed"],
                {"lifestyle": -10.0, "social": -10.0},
                "emergency_dispatch", "Priority Emergency Call Dispatched",
                "Automated emergency voice call & SMS dispatched to your designated emergency contact sharing your situation.",
                "IMMEDIATE_SAFETY"
            )

        if risk_level == "HIGH_CONCERN":
            return make_response(
                "It sounds like everything is piling up at once, and that's really exhausting. Talking to someone you trust, like a parent, favorite teacher, or counselor, could give you some real breathing room. How does that idea feel to you?",
                ["overwhelmed", "exhausted"],
                {"academic": -8.0, "lifestyle": -6.0},
                "trusted_human_referral", "Reach Out to a Trusted Mentor",
                "Consider speaking with a counselor, mentor, or parent about the pressure you're carrying.",
                "HIGH_CONCERN"
            )

        if any(kw in text_lower for kw in ["exam", "study", "test", "grade"]):
            return make_response(
                "Exams and school workload can feel like a nonstop weight on your shoulders. Are you finding any time during the day to step away and just catch your breath?",
                ["anxious"],
                {"academic": -6.0, "lifestyle": -3.0},
                "coping_strategy", "Micro Study Breaks",
                "Try 25 minutes of focused review followed by 5 minutes of stretching away from screens.",
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
                "Feeling disconnected from people around you is really tough. Even in a crowded room or online, loneliness can sneak in. Is there one person you usually feel most comfortable being yourself around?",
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
                "reasoning": "No distress signals detected; fallback active."
            },
            "pattern_observations": [],
            "escalation_requested": False,
        }
