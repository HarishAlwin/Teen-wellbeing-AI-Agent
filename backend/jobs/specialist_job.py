"""
backend/jobs/specialist_job.py
───────────────────────────────
Async background job that fires AFTER the chat response is returned to the user.

Execution flow (per chat turn):
  1. Receives dimension_signals from the completed WellbeingAnalyzer run
  2. Routes to only the active dimension specialists (re-uses keyword signals)
  3. Runs all active specialist calls concurrently via asyncio.gather
  4. Merges specialist outputs with the PatternDetector output passed in
  5. Writes merged result to WellbeingState cache (upsert, keyed by user_id)

Called via FastAPI BackgroundTasks — no broker, no separate process.
The chat turn is fully complete before this job starts.
If this job fails, the user experience is unaffected — it only enriches
the NEXT turn's LLM context.
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional

from database import SessionLocal
from services.specialist_agents import run_active_specialists
from services.wellbeing_state_cache import set_cached_state

logger = logging.getLogger("specialist_job")


async def _run_job(
    user_id: uuid.UUID,
    dimension_signals: Dict[str, List[str]],
    user_message: str,
    active_patterns: List[Dict[str, Any]],
    conversation_snippet: Optional[List[Dict[str, str]]] = None,
) -> None:
    """
    Core async job logic. Opens its own DB session since it runs outside the
    request lifecycle.
    """
    logger.info(f"[SpecialistJob] Starting background job for user {user_id}")

    try:
        # Run all active specialist calls concurrently
        specialist_results = await run_active_specialists(
            dimension_signals=dimension_signals,
            user_message=user_message,
            conversation_snippet=conversation_snippet,
        )

        # Build the merged wellbeing state
        merged_state: Dict[str, Any] = {
            "dimensions": specialist_results,  # only active dims
            "patterns": [
                {
                    "title": p.get("title"),
                    "category": p.get("category"),
                    "severity": p.get("severity"),
                    "dimensions_involved": p.get("dimensions_involved", []),
                    "source": p.get("source", "rule_based"),
                }
                for p in (active_patterns or [])
            ],
        }

        # Persist to cache using its own DB session
        db = SessionLocal()
        try:
            set_cached_state(db, user_id, merged_state)
            logger.info(
                f"[SpecialistJob] Cache updated for user {user_id} | "
                f"active_dims={list(specialist_results.keys())} | "
                f"patterns={len(merged_state['patterns'])}"
            )
        finally:
            db.close()

    except Exception as e:
        logger.error(f"[SpecialistJob] Background job failed for user {user_id}: {e}", exc_info=True)


def run_specialist_job(
    user_id: uuid.UUID,
    dimension_signals: Dict[str, List[str]],
    user_message: str,
    active_patterns: List[Dict[str, Any]],
    conversation_snippet: Optional[List[Dict[str, str]]] = None,
) -> None:
    """
    Synchronous wrapper called by FastAPI BackgroundTasks.
    Runs the async job in a new event loop so it doesn't interfere with
    the request event loop.
    """
    try:
        # FastAPI background tasks run in the same thread pool; create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                _run_job(
                    user_id=user_id,
                    dimension_signals=dimension_signals,
                    user_message=user_message,
                    active_patterns=active_patterns,
                    conversation_snippet=conversation_snippet,
                )
            )
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"[SpecialistJob] Fatal error in background wrapper: {e}", exc_info=True)
