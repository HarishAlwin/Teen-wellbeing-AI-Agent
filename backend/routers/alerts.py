from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid

from database import get_db
from models.escalation import Escalation
from models.user import User

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


class AcknowledgeRequest(BaseModel):
    pass


@router.get("")
async def list_alerts(db: Session = Depends(get_db)):
    """
    Counselor/guardian-facing view of every escalation ever triggered.
    This is intentionally a SEPARATE endpoint from anything the teenager's
    own frontend calls — it is not exposed on the chat/dashboard screens.
    """
    records = db.query(Escalation).order_by(Escalation.triggered_at.desc()).limit(100).all()

    results = []
    for r in records:
        user = db.query(User).filter(User.id == r.user_id).first()
        structured_json = None
        if r.calle_structured_result:
            try:
                import json
                structured_json = json.loads(r.calle_structured_result)
            except Exception:
                structured_json = r.calle_structured_result

        results.append({
            "id": str(r.id),
            "user_id": str(r.user_id),
            "user_display_name": user.display_name if user else "Unknown",
            "conversation_id": str(r.conversation_id) if r.conversation_id else None,
            "risk_level": r.risk_level,
            "reasons": r.reasons,
            "notified_channel": r.notified_channel,
            "call_sid": r.call_sid,
            "sms_sid": r.sms_sid,
            "calle_call_id": r.calle_call_id,
            "calle_task_completed": r.calle_task_completed,
            "calle_structured_result": structured_json,
            "status": r.status,
            "delivery_error": r.delivery_error,
            "triggered_at": r.triggered_at.isoformat() if r.triggered_at else None,
            "acknowledged_at": r.acknowledged_at.isoformat() if r.acknowledged_at else None,
        })

    return {"alerts": results, "count": len(results)}


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, db: Session = Depends(get_db)):
    from datetime import datetime
    try:
        a_uuid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID")

    record = db.query(Escalation).filter(Escalation.id == a_uuid).first()
    if not record:
        raise HTTPException(status_code=404, detail="Alert not found")

    record.status = "acknowledged"
    record.acknowledged_at = datetime.utcnow()
    db.commit()
    return {"status": "success"}
