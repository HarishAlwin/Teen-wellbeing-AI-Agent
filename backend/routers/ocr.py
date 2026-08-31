"""
backend/routers/ocr.py
──────────────────────
Endpoint for the Multimodal OCR Agent.
Allows teenagers/counselors to upload images of notes, exam papers, schedules,
or chat logs for text extraction and wellbeing context analysis.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from database import get_db
from services.ocr_service import OCRService
from services.llm_agent import LLMAgent
from models.user import User

router = APIRouter(prefix="/api/ocr", tags=["OCR Agent"])


@router.post("/analyze")
async def analyze_image_document(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    conversation_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload an image file (PNG, JPG, WEBP, PDF screenshot) for OCR text extraction
    and automated wellbeing insight generation via Groq Vision + LLM.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No image file provided")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    content_type = file.content_type or "image/jpeg"

    # Step 1: Run OCR Service using Groq Vision
    ocr_result = await OCRService.extract_and_analyze(image_bytes, content_type)

    # Step 2: If text was extracted, generate an empathetic Jarvis companion breakdown
    extracted_text = ocr_result.get("extracted_text", "")
    summary = ocr_result.get("summary", "")
    doc_type = ocr_result.get("document_type", "document")
    wellbeing = ocr_result.get("wellbeing_indicators", {})

    agent_response = LLMAgent.generate_response(
        user_message=f"I've uploaded a photo of my {doc_type}. Here is what's in it: '{extracted_text}'. {summary}",
        conversation_history=[],
        current_scores={"social": 70, "family": 70, "academic": 65, "digital": 65, "lifestyle": 68},
        active_patterns=[],
        risk_level="NORMAL",
        safety_guidance={},
        user_id=user_id,
    )

    return {
        "filename": file.filename,
        "ocr_result": ocr_result,
        "ai_companion_reply": agent_response.get("response_text", ""),
        "dimension_impacts": agent_response.get("dimension_impacts", {}),
        "risk_assessment": agent_response.get("risk_assessment", {}),
        "intervention": agent_response.get("intervention")
    }
