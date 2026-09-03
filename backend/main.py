import os
import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from database import engine, Base
import models
from routers import chat, speech, dashboard, profile, alerts

load_dotenv()

# --- Logging setup ---------------------------------------------------------
# Previously the app had no logging configuration, so backend crashes during
# a request (e.g. an unhandled exception in chat.py) were easy to miss in the
# terminal. This ensures every request error is printed with a full traceback.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aura")

# Create all database tables automatically on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Teen Wellbeing Intelligence API",
    description="Voice-First AI Wellbeing Companion & Early Pattern Detection System",
    version="1.0.0"
)

# CORS configuration
allowed_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Global exception handler -----------------------------------------------
# Previously, any unhandled exception inside a route (e.g. chat.py) would
# result in FastAPI's default 500 response, and the frontend would catch the
# network-level failure and silently replace it with a fake "glitch"
# message — hiding the real cause. This handler guarantees:
#  1. The full traceback is always printed to the backend terminal.
#  2. The frontend gets a real, readable error message in the JSON response
#     instead of just a failed fetch, so it can be surfaced honestly to the
#     user/developer rather than papered over.
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error(
        "Unhandled exception on %s %s\n%s",
        request.method, request.url.path, tb
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": str(exc) or "An unexpected error occurred.",
            "path": str(request.url.path),
        },
    )


# Mount routers
app.include_router(chat.router)
app.include_router(speech.router)
app.include_router(dashboard.router)
app.include_router(profile.router)
app.include_router(alerts.router)


@app.get("/")
def read_root():
    return {
        "system": "Teen Wellbeing Intelligence — Voice-First AI",
        "status": "operational",
        "version": "1.0.0",
        "docs": "/docs",
        "responsible_ai_notice": "This system provides preventive wellbeing companionship and pattern detection, not clinical diagnosis."
    }


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}
