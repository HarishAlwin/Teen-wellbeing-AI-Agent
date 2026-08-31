"""
backend/models/user.py
──────────────────────
User and Session SQLAlchemy models.

Schema additions (P0 security upgrade):
  email          — unique, nullable (guest users have no email)
  hashed_password — nullable (guest/demo users have no password)
  role           — "user" (default) | "counselor" | "guardian"
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, text
from sqlalchemy.orm import relationship
from database import Base
from models.guid import GUID


class User(Base):
    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200), nullable=True)
    email = Column(String(255), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)  # nullable: guest/demo users have no password
    role = Column(String(30), default="user", nullable=False)  # user | counselor | guardian
    country_code = Column(String(5), default="IN")
    age_group = Column(String(20), default="teen")          # teen | young_adult
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_demo = Column(Boolean, default=False)

    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("WellbeingProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    emergency_contacts = relationship("EmergencyContact", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, nullable=False)
    token = Column(String(512), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


def run_user_migrations(engine):
    """
    Safe ALTER TABLE migration for the users table.
    Adds new columns introduced in the P0 security upgrade.
    Inspects existing columns first to prevent PostgreSQL transaction aborts.

    Call this from main.py startup after Base.metadata.create_all().
    """
    import logging
    from sqlalchemy import inspect
    logger = logging.getLogger("migrations")

    new_columns = [
        ("email", "VARCHAR(255)"),
        ("hashed_password", "VARCHAR(255)"),
        ("role", "VARCHAR(30) DEFAULT 'user' NOT NULL"),
    ]

    existing_cols = set()
    try:
        inspector = inspect(engine)
        existing_cols = {c["name"] for c in inspector.get_columns("users")}
    except Exception as e:
        logger.warning(f"[Migration] Could not inspect columns: {e}")

    for col_name, col_def in new_columns:
        if col_name in existing_cols:
            logger.debug(f"[Migration] Column users.{col_name} already exists — skipped.")
            continue
        try:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
            logger.info(f"[Migration] Added column users.{col_name}")
        except Exception as e:
            err_str = str(e).lower()
            if "duplicate" in err_str or "already exists" in err_str or "duplicate column" in err_str:
                logger.debug(f"[Migration] Column users.{col_name} already exists — skipped.")
            else:
                logger.warning(f"[Migration] Unexpected error adding users.{col_name}: {e}")


