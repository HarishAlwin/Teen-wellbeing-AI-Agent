import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import engine, Base
import models
from routers import chat, speech, dashboard, profile

load_dotenv()

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

# Mount routers
app.include_router(chat.router)
app.include_router(speech.router)
app.include_router(dashboard.router)
app.include_router(profile.router)

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
