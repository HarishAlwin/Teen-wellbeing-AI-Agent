"""
backend/auth.py
───────────────
Minimal custom JWT authentication for Teen Wellbeing Intelligence API.

Provides:
  - Password hashing/verification via bcrypt (passlib)
  - JWT creation/verification via python-jose (HS256)
  - FastAPI dependencies:
      get_current_user  → any authenticated user
      require_role(...)  → parameterized role gate (e.g., "counselor")

Roles:
  "user"      — teen/standard user (default)
  "counselor" — school counselor / administrator (can view /api/alerts)
  "guardian"  — parent/guardian (future use, reserved)
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel

try:
    from passlib.context import CryptContext
    from jose import JWTError, jwt
    _auth_deps_available = True
except ImportError:
    _auth_deps_available = False

from database import get_db

logger = logging.getLogger("auth")

# ── Configuration ─────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24h default
GUEST_TOKEN_EXPIRE_MINUTES = 60  # Guest sessions are short-lived (1h)

if not SECRET_KEY:
    logger.critical(
        "[Auth] CRITICAL: JWT_SECRET_KEY is not set. "
        "All token operations will fail. Set JWT_SECRET_KEY in .env before deployment."
    )

# ── Password hashing ───────────────────────────────────────────────────────────
if _auth_deps_available:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(plain: str) -> str:
        return pwd_context.hash(plain)

    def verify_password(plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)
else:
    def hash_password(plain: str) -> str:
        raise RuntimeError("passlib not installed. Run: pip install passlib[bcrypt]")

    def verify_password(plain: str, hashed: str) -> bool:
        raise RuntimeError("passlib not installed. Run: pip install passlib[bcrypt]")


# ── Token data schema ──────────────────────────────────────────────────────────
class TokenData(BaseModel):
    user_id: str
    role: str = "user"
    is_guest: bool = False


# ── JWT creation ───────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Sign a HS256 JWT with the given payload. Raises RuntimeError if deps missing."""
    if not _auth_deps_available:
        raise RuntimeError("python-jose not installed. Run: pip install python-jose[cryptography]")
    if not SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not set in environment.")

    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> TokenData:
    """Decode and validate a JWT. Raises HTTPException 401 on any failure."""
    if not _auth_deps_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth dependencies not installed on server."
        )
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role", "user")
        is_guest: bool = payload.get("is_guest", False)
        if user_id is None:
            raise credentials_exception
        return TokenData(user_id=user_id, role=role, is_guest=is_guest)
    except JWTError:
        raise credentials_exception


# ── FastAPI security scheme ────────────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """
    FastAPI dependency: validates Bearer token and returns the User ORM object.
    Raises 401 if token is invalid or expired.
    Raises 404 if the user no longer exists in the database.
    """
    from models.user import User
    token_data = verify_token(credentials.credentials)
    import uuid
    try:
        u_uuid = uuid.UUID(token_data.user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    user = db.query(User).filter(User.id == u_uuid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def require_role(*allowed_roles: str):
    """
    Parameterized dependency factory for role-based access control.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("counselor"))])
        async def admin_endpoint(current_user=Depends(get_current_user)):
            ...

    Or as a combined dependency:
        @router.get("/admin")
        async def admin_endpoint(current_user=Depends(require_role("counselor"))):
            ...
    """
    def _check_role(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        db: Session = Depends(get_db),
    ):
        from models.user import User
        token_data = verify_token(credentials.credentials)

        # Validate role from token
        if token_data.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {list(allowed_roles)}. "
                       f"Your role: '{token_data.role}'."
            )

        # Confirm user still exists in DB
        import uuid
        try:
            u_uuid = uuid.UUID(token_data.user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

        user = db.query(User).filter(User.id == u_uuid).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Double-check role in DB (token role is a cache; DB is authoritative)
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Insufficient role: '{user.role}'"
            )
        return user

    return _check_role
