from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid

from database import get_db
from models.user import User
from models.profile import WellbeingProfile

router = APIRouter(prefix="/api/profile", tags=["Profile"])

class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    country_code: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

@router.get("/{user_id}")
async def get_profile(user_id: str, db: Session = Depends(get_db)):
    try:
        u_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user = db.query(User).filter(User.id == u_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = db.query(WellbeingProfile).filter(WellbeingProfile.user_id == user.id).first()
    return {
        "user_id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "country_code": user.country_code,
        "profile": {
            "risk_level": profile.risk_level if profile else "NORMAL",
            "current_scores": {
                "social": profile.current_social if profile else 70.0,
                "family": profile.current_family if profile else 70.0,
                "academic": profile.current_academic if profile else 70.0,
                "digital": profile.current_digital if profile else 70.0,
                "lifestyle": profile.current_lifestyle if profile else 70.0,
            },
            "preferences": profile.preferences if profile else {}
        }
    }

@router.put("/{user_id}")
async def update_profile(user_id: str, req: ProfileUpdateRequest, db: Session = Depends(get_db)):
    try:
        u_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user = db.query(User).filter(User.id == u_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if req.display_name is not None:
        user.display_name = req.display_name
    if req.country_code is not None:
        user.country_code = req.country_code

    profile = db.query(WellbeingProfile).filter(WellbeingProfile.user_id == user.id).first()
    if profile and req.preferences is not None:
        profile.preferences = req.preferences

    db.commit()
    return {"status": "success", "message": "Profile updated successfully"}
