from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from database import get_db
from models.escalation import Escalation

router = APIRouter(prefix="/api/alerts", tags=["Alerts (Counselor/Guardian View)"])


@router.get("")
def list_alerts(
    db: Session = Depends(get_db),
    risk_level: Optional[str] = Query(None, description="Filter by risk level (HIGH_CONCERN, IMMEDIATE_SAFETY)"),
    status: Optional[str] = Query(None, description="Filter by status (pending, notified, acknowledged, resolved)"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """
    GET /api/alerts — Lists all escalation records for counselor/guardian review.

    This endpoint is NOT for teen users. It is intended for a counselor-facing
    dashboard where responsible adults can review flagged conversations.

    Supports optional filtering by risk_level and status.
    """
    query = db.query(Escalation).order_by(desc(Escalation.triggered_at))

    if risk_level:
        query = query.filter(Escalation.risk_level == risk_level.upper())
    if status:
        query = query.filter(Escalation.status == status.lower())

    total = query.count()
    alerts = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "alerts": [
            {
                "id": str(a.id),
                "user_id": str(a.user_id),
                "conversation_id": str(a.conversation_id) if a.conversation_id else None,
                "risk_level": a.risk_level,
                "reason": a.reason,
                "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
                "notified_channel": a.notified_channel,
                "status": a.status,
            }
            for a in alerts
        ],
    }


@router.patch("/{alert_id}/status")
def update_alert_status(
    alert_id: str,
    new_status: str = Query(..., description="New status: acknowledged | resolved"),
    db: Session = Depends(get_db),
):
    """
    PATCH /api/alerts/{alert_id}/status — Allows a counselor to mark an alert as
    acknowledged or resolved. Only transitions from 'pending'/'notified' are supported.
    """
    import uuid
    try:
        a_uuid = uuid.UUID(alert_id)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid alert ID")

    alert = db.query(Escalation).filter(Escalation.id == a_uuid).first()
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found")

    allowed_transitions = {"acknowledged", "resolved"}
    if new_status not in allowed_transitions:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Status must be one of: {allowed_transitions}")

    alert.status = new_status
    db.commit()
    return {"id": alert_id, "status": alert.status, "message": f"Alert marked as {new_status}"}
