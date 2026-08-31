"""
backend/routers/auth.py
────────────────────────
Authentication endpoints. No auth required on any route here.

Routes:
  POST /api/auth/register  — create a full account (email + password)
  POST /api/auth/login     — authenticate and receive a JWT
  POST /api/auth/guest     — create an anonymous demo session (short-lived JWT)
  GET  /api/auth/me        — return current user info (requires token)

Guest flow preserves the existing demo UX: the frontend can call /api/auth/guest
and receive a 1-hour token without any login screen. Counselor accounts must use
/api/auth/register with role specified, or be promoted via the DB.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator

from database import get_db
from models.user import User
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    GUEST_TOKEN_EXPIRE_MINUTES,
)

logger = logging.getLogger("auth_router")
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ── Request / Response schemas ─────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    display_name: Optional[str] = None
    country_code: Optional[str] = "IN"
    role: Optional[str] = "user"  # only "user" by default; "counselor" requires admin setup

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        allowed = {"user", "counselor", "guardian"}
        if v not in allowed:
            raise ValueError(f"role must be one of: {allowed}")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class GuestRequest(BaseModel):
    display_name: Optional[str] = "Alex"
    country_code: Optional[str] = "IN"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user_id: str
    role: str
    is_guest: bool = False


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Create a new full account. Returns a JWT on success.

    Note: Setting role="counselor" is allowed here for development convenience.
    In production, counselor accounts should be provisioned by an admin.
    """
    # Check for duplicate email
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )

    # Check for duplicate username
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken."
        )

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        display_name=req.display_name or req.username,
        country_code=req.country_code or "IN",
        role=req.role,
        is_demo=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "is_guest": False},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info(f"[Auth] New user registered: {user.username} (role={user.role})")
    return TokenResponse(
        access_token=token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        role=user.role,
        is_guest=False,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email + password. Returns a JWT."""
    user = db.query(User).filter(User.email == req.email).first()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Update last_seen
    user.last_seen = datetime.utcnow()
    db.commit()

    token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "is_guest": False},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info(f"[Auth] User logged in: {user.username} (role={user.role})")
    return TokenResponse(
        access_token=token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        role=user.role,
        is_guest=False,
    )


@router.post("/guest", response_model=TokenResponse)
async def guest_session(req: GuestRequest, db: Session = Depends(get_db)):
    """
    Create an anonymous guest session with a short-lived JWT (1 hour).

    This preserves the existing demo UX: no email/password required.
    Guest users have role="user" and is_demo=True.
    The frontend should call this on first load if no stored token exists.
    """
    guest_user = User(
        username=f"guest_{str(uuid.uuid4())[:8]}",
        display_name=req.display_name or "Alex",
        country_code=req.country_code or "IN",
        role="user",
        is_demo=True,
    )
    db.add(guest_user)
    db.commit()
    db.refresh(guest_user)

    token = create_access_token(
        data={"sub": str(guest_user.id), "role": "user", "is_guest": True},
        expires_delta=timedelta(minutes=GUEST_TOKEN_EXPIRE_MINUTES),
    )
    logger.info(f"[Auth] Guest session created: {guest_user.username}")
    return TokenResponse(
        access_token=token,
        expires_in=GUEST_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(guest_user.id),
        role="user",
        is_guest=True,
    )


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user's info."""
    return {
        "user_id": str(current_user.id),
        "username": current_user.username,
        "display_name": current_user.display_name,
        "email": current_user.email,
        "role": current_user.role,
        "is_guest": current_user.is_demo,
        "country_code": current_user.country_code,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }
