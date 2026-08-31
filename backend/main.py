import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import engine, Base
import models
from routers import chat, speech, profile, alerts, ocr
from routers import auth as auth_router
from routers import contacts as contacts_router

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")


def _validate_startup_config():
    """
    Warn loudly at startup if critical secrets are missing or look like defaults.
    This catches .env misconfiguration before it causes silent failures.
    """
    checks = {
        "JWT_SECRET_KEY": (os.getenv("JWT_SECRET_KEY", ""), 32, "Auth token signing will fail"),
        "GROQ_API_KEY": (os.getenv("GROQ_API_KEY", ""), 20, "LLM calls will use fallback responses"),
    }
    for var, (val, min_len, consequence) in checks.items():
        if not val:
            logger.critical(f"[Startup] CRITICAL: {var} is not set. {consequence}.")
        elif len(val) < min_len:
            logger.warning(f"[Startup] WARNING: {var} looks suspiciously short ({len(val)} chars). "
                           f"Verify it is a valid key. {consequence}.")
        elif val in ("your_groq_api_key_here", "your_gemini_api_key_here",
                     "teen_wellbeing_secret_key_development_32_chars",
                     "change_me_in_production_random_32_chars"):
            logger.critical(f"[Startup] CRITICAL: {var} is set to a placeholder/default value. "
                            f"Replace it with a real secret. {consequence}.")


# Create all database tables automatically on startup
Base.metadata.create_all(bind=engine)

# Run incremental column migrations for existing tables (safe no-op if columns exist)
from models.user import run_user_migrations
run_user_migrations(engine)

_validate_startup_config()

app = FastAPI(
    title="Teen Wellbeing Intelligence API",
    description="Voice-First AI Wellbeing Companion & Early Pattern Detection System",
    version="2.0.0"
)

# CORS configuration
allowed_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:.*|http://127.0.0.1:.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth_router.router)    # /api/auth — no auth required
app.include_router(chat.router)           # /api/chat — requires auth
app.include_router(speech.router)
app.include_router(profile.router)        # /api/profile — requires auth
app.include_router(alerts.router)         # /api/alerts — requires counselor role
app.include_router(ocr.router)
app.include_router(contacts_router.router)  # /api/contacts — requires auth

@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return {
        "system": "Teen Wellbeing Intelligence — Voice-First AI",
        "status": "operational",
        "version": "2.0.0",
        "docs": "/docs",
        "auth": "JWT Bearer token required on all /api/chat, /api/alerts, /api/profile, /api/contacts routes",
        "responsible_ai_notice": "This system provides preventive wellbeing companionship and pattern detection, not clinical diagnosis."
    }

@app.api_route("/health", methods=["GET", "HEAD"])
@app.api_route("/api/health", methods=["GET", "HEAD"])
def health_check():
    return {"status": "healthy"}


