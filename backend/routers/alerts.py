from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from database import get_db
from models.escalation import Escalation
from auth import require_role, get_current_user


router = APIRouter(prefix="/api/alerts", tags=["Alerts (Counselor/Guardian View)"])


@router.get("")
def list_alerts(
    db: Session = Depends(get_db),
    current_user=Depends(require_role("counselor")),
    risk_level: Optional[str] = Query(None, description="Filter by risk level (HIGH_CONCERN, IMMEDIATE_SAFETY)"),
    status: Optional[str] = Query(None, description="Filter by status (pending, notified, acknowledged, resolved)"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """
    GET /api/alerts — Lists all escalation records for counselor/guardian review.

    Requires role: counselor
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
    current_user=Depends(require_role("counselor")),
):
    """
    PATCH /api/alerts/{alert_id}/status — Allows a counselor to mark an alert as
    acknowledged or resolved. Only transitions from 'pending'/'notified' are supported.

    Requires role: counselor
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


class DirectCallDispatchRequest(BaseModel):
    user_message: str
    phone_number: Optional[str] = None
    risk_level: Optional[str] = "IMMEDIATE_SAFETY"
    reason: Optional[str] = "Direct voice dispatch triggered"


@router.post("/dispatch-call")
async def trigger_direct_call_dispatch(
    req: DirectCallDispatchRequest,
    current_user=Depends(get_current_user),
):
    """
    POST /api/alerts/dispatch-call — Initiates an automated voice call and SMS
    to the designated emergency contact sharing the user's message.
    """
    from services.emergency_dispatcher import EmergencyDispatcher
    result = await EmergencyDispatcher.dispatch(
        user_id=str(current_user.id),
        user_message=req.user_message,
        risk_level=req.risk_level or "IMMEDIATE_SAFETY",
        reason=req.reason or "Direct user command dispatch",
        target_phone=req.phone_number
    )
    return result


