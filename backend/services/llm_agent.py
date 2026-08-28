import os
import json
from typing import Dict, Any, List, Optional

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
    "content": "Try leaving the phone across the room 20 minutes before sleep."
  },
  "suggested_risk_level": "NORMAL"
}
"""

class LLMAgent:
    """
    Core conversational agent powered by Google Gemini with graceful fallback.
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
        user_profile: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generates empathetic response with context injection.
        """
        if llm_available and genai:
            try:
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=SYSTEM_PROMPT,
                    generation_config={"response_mime_type": "application/json", "temperature": 0.7}
                )

                context_prompt = f"""
Current User State:
- Current Wellbeing Scores: {json.dumps(current_scores)}
- Active Life Patterns: {json.dumps([p.get('title') for p in active_patterns])}
- Current Safety Assessment: {risk_level}
- Safety Guidance: {safety_guidance.get('message', '')}
- Conversation History:
{json.dumps(conversation_history[-6:])}

Teenager says:
"{user_message}"
"""
                response = model.generate_content(context_prompt)
                parsed = json.loads(response.text)
                return parsed
            except Exception as e:
                print(f"[LLMAgent] Gemini call failed, using intelligent fallback: {e}")

        # Intelligent deterministic fallback
        return cls._fallback_response(user_message, current_scores, active_patterns, risk_level, safety_guidance)

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
            return {
                "response_text": "I can hear how much pain you're in right now, and I want you to know you don't have to carry this alone. Please reach out to someone who can help keep you safe — a family member, a counselor, or the free 24/7 helplines right on your screen.",
                "emotions_detected": ["hopeless", "distressed"],
                "dimension_impacts": {"lifestyle": -10.0, "social": -10.0},
                "intervention": {
                    "needed": True,
                    "type": "emergency_helpline",
                    "title": "Immediate Care & Support",
                    "content": "Please connect with a trusted person or free crisis helpline right away."
                },
                "suggested_risk_level": "IMMEDIATE_SAFETY"
            }

        if risk_level == "HIGH_CONCERN":
            return {
                "response_text": "It sounds like everything is piling up at once, and that's really exhausting. You don't have to navigate this completely on your own — talking to someone you trust, like a favorite teacher, parent, or counselor, could give you some real breathing room. How does that idea feel to you?",
                "emotions_detected": ["overwhelmed", "exhausted"],
                "dimension_impacts": {"academic": -8.0, "lifestyle": -6.0},
                "intervention": {
                    "needed": True,
                    "type": "trusted_human_referral",
                    "title": "Reach Out to a Trusted Mentor",
                    "content": "Consider speaking with a counselor, mentor, or parent about the pressure you're carrying."
                },
                "suggested_risk_level": "HIGH_CONCERN"
            }

        # Pattern-specific conversational handling
        if "exam" in text_lower or "study" in text_lower or "test" in text_lower or "grade" in text_lower:
            return {
                "response_text": "Exams and school workload can feel like a nonstop weight on your shoulders, especially when you want to do well. Are you finding any time during the day to step away and just catch your breath?",
                "emotions_detected": ["anxious"],
                "dimension_impacts": {"academic": -6.0, "lifestyle": -3.0},
                "intervention": {
                    "needed": True,
                    "type": "coping_strategy",
                    "title": "Micro Study Breaks",
                    "content": "Try 25 minutes of focused review followed by 5 minutes of stretching or music away from screens."
                },
                "suggested_risk_level": "NORMAL"
            }

        if "sleep" in text_lower or "tired" in text_lower or "phone" in text_lower or "scroll" in text_lower:
            return {
                "response_text": "It’s so easy to stay up late scrolling just to get some free time to yourself, but waking up completely drained makes the whole next day harder. What time do you usually end up putting your phone down at night?",
                "emotions_detected": ["exhausted"],
                "dimension_impacts": {"digital": -5.0, "lifestyle": -5.0},
                "intervention": {
                    "needed": True,
                    "type": "routine_suggestion",
                    "title": "Night Wind-Down Routine",
                    "content": "Switch your screen to night mode or listen to a relaxing audio track 20 minutes before sleeping."
                },
                "suggested_risk_level": "NORMAL"
            }

        if "lonely" in text_lower or "friend" in text_lower or "people" in text_lower:
            return {
                "response_text": "Feeling disconnected from the people around you is really tough. Even in a crowded room or online, loneliness can sneak in. Is there one person you usually feel most comfortable being yourself around?",
                "emotions_detected": ["lonely"],
                "dimension_impacts": {"social": -5.0},
                "intervention": {
                    "needed": True,
                    "type": "reflective_question",
                    "title": "Reconnect with One Person",
                    "content": "Send a simple low-pressure message to a friend you haven't caught up with recently."
                },
                "suggested_risk_level": "NORMAL"
            }

        # General friendly check-in
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
            "suggested_risk_level": "NORMAL"
        }
