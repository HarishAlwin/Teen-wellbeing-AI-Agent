"""
backend/services/wellbeing_state_cache.py
──────────────────────────────────────────
Persistent cache for the merged specialist-agent + PatternDetector output
produced by the async background job (backend/jobs/specialist_job.py).

The chat fast-path reads this cache to enrich the LLM context prompt without
blocking on specialist calls. If the cache is empty (first message, or job
hasn't run yet), the chat turn proceeds identically to the pre-upgrade behavior.

Model: WellbeingState — one row per user_id (upsert pattern).
"""

import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.orm import Session

from database import Base
from models.guid import GUID

logger = logging.getLogger("wellbeing_state_cache")


# ── ORM Model ─────────────────────────────────────────────────────────────────

class WellbeingState(Base):
    """
    One row per user. Holds the latest merged output from the 5 specialist
    agents + PatternDetector. Updated by the async background job after each
    chat turn (for dimensions that were active in that turn).
    """
    __tablename__ = "wellbeing_state_cache"

    # Unique per user — this is an upsert-pattern table, not a time-series
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, unique=True, nullable=False)

    # JSON payload: merged specialist outputs + pattern detector summary
    # Structure:
    # {
    #   "dimensions": {
    #     "social":    {"score_delta": 0.0, "insights": [...], "flags": [...]},
    #     "family":    {...},
    #     "academic":  {...},
    #     "digital":   {...},
    #     "lifestyle": {...}
    #   },
    #   "patterns": [...],          # from PatternDetector
    #   "job_ran_at": "ISO-8601",   # when the last background job completed
    #   "turns_processed": 0        # cumulative count
    # }
    state_json = Column(JSON, default=dict, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ── Cache API ─────────────────────────────────────────────────────────────────

def get_cached_state(db: Session, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """
    Retrieve the latest cached wellbeing state for a user.
    Returns None if no job has run yet for this user.
    """
    record = db.query(WellbeingState).filter(WellbeingState.user_id == user_id).first()
    if not record or not record.state_json:
        return None
    return record.state_json


def set_cached_state(db: Session, user_id: uuid.UUID, state: Dict[str, Any]) -> None:
    """
    Upsert the wellbeing state cache for a user.
    Merges new state into existing record if present, or creates a new one.
    """
    record = db.query(WellbeingState).filter(WellbeingState.user_id == user_id).first()

    state["job_ran_at"] = datetime.utcnow().isoformat()

    if record:
        # Merge: update only dimensions that the current job touched
        existing = dict(record.state_json or {})
        existing_dims = existing.get("dimensions", {})
        new_dims = state.get("dimensions", {})
        existing_dims.update(new_dims)  # only touched dimensions are overwritten
        existing["dimensions"] = existing_dims
        existing["patterns"] = state.get("patterns", existing.get("patterns", []))
        existing["job_ran_at"] = state["job_ran_at"]
        existing["turns_processed"] = existing.get("turns_processed", 0) + 1
        record.state_json = existing
        record.updated_at = datetime.utcnow()
    else:
        state.setdefault("turns_processed", 1)
        record = WellbeingState(user_id=user_id, state_json=state)
        db.add(record)

    try:
        db.commit()
        logger.debug(f"[WellbeingStateCache] Updated cache for user {user_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"[WellbeingStateCache] Failed to update cache: {e}")
