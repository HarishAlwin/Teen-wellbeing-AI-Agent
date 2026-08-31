"""
backend/services/specialist_agents.py
──────────────────────────────────────
Five lightweight dimension-specific specialist agents.

Each specialist is a compact Groq call scoped to ONE dimension.
Uses llama-3.1-8b-instant (fast, cheap) — NOT the 70B model.

Routing: run_specialist() is only called if WellbeingAnalyzer found keyword
matches for that dimension in the current turn (neg_matches or pos_matches).
This re-uses the existing keyword router and avoids redundant API calls.

These run in the ASYNC BACKGROUND (via FastAPI BackgroundTasks in chat.py) —
they do NOT block the chat response.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional

logger = logging.getLogger("specialist_agents")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# Specialist calls use the lightweight model to minimise latency and cost
SPECIALIST_MODEL = os.getenv("GROQ_SPECIALIST_MODEL", "groq/compound-mini")
SPECIALIST_FALLBACK_MODELS = ["groq/compound-mini", "groq/compound", "openai/gpt-oss-20b"]

groq_client = None
try:
    if GROQ_API_KEY and GROQ_API_KEY != "your_groq_api_key_here":
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    logger.warning(f"[SpecialistAgents] Could not initialize Groq client: {e}")


# ── Per-dimension system prompts ───────────────────────────────────────────────

SPECIALIST_PROMPTS = {
    "social": """\
You are a Social Wellbeing Specialist analyzing a single message from a teenager.
Focus ONLY on social dimension signals: peer relationships, friendship quality,
loneliness, belonging, bullying, social anxiety, and group dynamics.

Respond ONLY with a JSON object:
{
  "dimension": "social",
  "score_delta": <float, -10 to +10, negative means worsening>,
  "insights": ["concise observation 1", "concise observation 2"],
  "flags": ["loneliness"|"isolation"|"bullying"|"social_anxiety"|"conflict"|"positive_social"|"none"]
}
""",
    "family": """\
You are a Family Wellbeing Specialist analyzing a single message from a teenager.
Focus ONLY on family dimension signals: parental relationships, home atmosphere,
family conflict, sibling dynamics, expectations, support, and communication.

Respond ONLY with a JSON object:
{
  "dimension": "family",
  "score_delta": <float, -10 to +10, negative means worsening>,
  "insights": ["concise observation 1", "concise observation 2"],
  "flags": ["conflict"|"pressure"|"unsupported"|"positive_family"|"comparison"|"none"]
}
""",
    "academic": """\
You are an Academic Wellbeing Specialist analyzing a single message from a teenager.
Focus ONLY on academic dimension signals: exam stress, assignment load, grades,
procrastination, fear of failure, college pressure, and academic motivation.

Respond ONLY with a JSON object:
{
  "dimension": "academic",
  "score_delta": <float, -10 to +10, negative means worsening>,
  "insights": ["concise observation 1", "concise observation 2"],
  "flags": ["exam_anxiety"|"overload"|"fear_of_failure"|"procrastination"|"positive_academic"|"none"]
}
""",
    "digital": """\
You are a Digital Wellbeing Specialist analyzing a single message from a teenager.
Focus ONLY on digital dimension signals: excessive screen time, late-night phone
use, doomscrolling, social media comparison, cyberbullying, gaming addiction,
and notification stress.

Respond ONLY with a JSON object:
{
  "dimension": "digital",
  "score_delta": <float, -10 to +10, negative means worsening>,
  "insights": ["concise observation 1", "concise observation 2"],
  "flags": ["excessive_screen"|"doomscrolling"|"social_comparison"|"late_night_phone"|"positive_digital"|"none"]
}
""",
    "lifestyle": """\
You are a Lifestyle Wellbeing Specialist analyzing a single message from a teenager.
Focus ONLY on lifestyle dimension signals: sleep quality, fatigue, nutrition,
physical activity, energy levels, headaches, and daily routine irregularity.

Respond ONLY with a JSON object:
{
  "dimension": "lifestyle",
  "score_delta": <float, -10 to +10, negative means worsening>,
  "insights": ["concise observation 1", "concise observation 2"],
  "flags": ["poor_sleep"|"fatigue"|"poor_nutrition"|"sedentary"|"positive_lifestyle"|"none"]
}
""",
}


def _fallback_specialist_result(dimension: str) -> Dict[str, Any]:
    """Returns a neutral no-op result when Groq is unavailable."""
    return {
        "dimension": dimension,
        "score_delta": 0.0,
        "insights": [],
        "flags": ["none"],
        "source": "fallback",
    }


async def run_specialist(
    dimension: str,
    user_message: str,
    conversation_snippet: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Run a single dimension specialist LLM call asynchronously.

    Args:
        dimension: One of "social", "family", "academic", "digital", "lifestyle"
        user_message: The latest user message text
        conversation_snippet: Last 3 messages for context (optional)

    Returns:
        Dict with dimension, score_delta, insights, flags, source
    """
    if dimension not in SPECIALIST_PROMPTS:
        logger.warning(f"[SpecialistAgents] Unknown dimension: {dimension}")
        return _fallback_specialist_result(dimension)

    if not groq_client:
        logger.debug(f"[SpecialistAgents] Groq unavailable, returning fallback for {dimension}")
        return _fallback_specialist_result(dimension)

    system_prompt = SPECIALIST_PROMPTS[dimension]

    context_text = ""
    if conversation_snippet:
        last_3 = conversation_snippet[-3:]
        context_text = "\n".join(
            f"[{m['role'].upper()}]: {m['content']}" for m in last_3
        )
        context_text = f"\nRecent context:\n{context_text}\n"

    user_prompt = f"{context_text}\nLatest message to analyze:\n\"{user_message}\""

    models_to_try = [SPECIALIST_MODEL] + [m for m in SPECIALIST_FALLBACK_MODELS if m != SPECIALIST_MODEL]

    for model_name in models_to_try:
        try:
            # Run synchronous Groq call in a thread pool to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda m=model_name: groq_client.chat.completions.create(
                    model=m,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                    max_tokens=256,
                )
            )
            raw = response.choices[0].message.content
            result = json.loads(raw)
            result["source"] = "specialist_llm"
            # Clamp score_delta to safe range
            result["score_delta"] = max(-10.0, min(10.0, float(result.get("score_delta", 0.0))))
            logger.debug(f"[SpecialistAgents] {dimension} → delta={result['score_delta']}, flags={result.get('flags')}")
            return result

        except Exception as e:
            logger.warning(f"[SpecialistAgents] {dimension} specialist failed on {model_name}: {e}")

    return _fallback_specialist_result(dimension)



async def run_active_specialists(
    dimension_signals: Dict[str, List[str]],
    user_message: str,
    conversation_snippet: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Run specialist calls concurrently for all dimensions that had active signals
    in the current turn (at least one neg or pos keyword match).

    Args:
        dimension_signals: Output of WellbeingAnalyzer.analyze_message()["dimension_signals"]
                           e.g. {"academic": ["negative: exam", "negative: cramming"], "social": [], ...}
        user_message: Raw user message text
        conversation_snippet: Recent conversation history for context

    Returns:
        Dict mapping dimension → specialist result (only for active dimensions)
    """
    active_dims = [
        dim for dim, signals in dimension_signals.items()
        if signals  # non-empty list means this dimension had keyword matches
    ]

    if not active_dims:
        logger.debug("[SpecialistAgents] No active dimensions — skipping all specialist calls")
        return {}

    logger.info(f"[SpecialistAgents] Running specialists for active dimensions: {active_dims}")

    # Run all active specialist calls concurrently
    tasks = [
        run_specialist(dim, user_message, conversation_snippet)
        for dim in active_dims
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output = {}
    for dim, result in zip(active_dims, results):
        if isinstance(result, Exception):
            logger.warning(f"[SpecialistAgents] {dim} raised exception: {result}")
            output[dim] = _fallback_specialist_result(dim)
        else:
            output[dim] = result

    return output
