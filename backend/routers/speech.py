from fastapi import APIRouter, UploadFile, File, Response, HTTPException
from pydantic import BaseModel
from services.speech_service import SpeechService

router = APIRouter(prefix="/api/speech", tags=["Speech"])

class SynthesizeRequest(BaseModel):
    text: str

@router.post("/transcribe")
async def transcribe_audio_endpoint(file: UploadFile = File(...)):
    """
    Accepts recorded voice audio (WebM / WAV / MP3 / OGG) and transcribes via Deepgram STT.
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    transcript = await SpeechService.transcribe_audio(audio_bytes, file.content_type or "audio/webm")
    return {"transcript": transcript}

@router.post("/synthesize")
async def synthesize_speech_endpoint(req: SynthesizeRequest):
    """
    Accepts text and synthesizes speech audio via ElevenLabs TTS, returning MP3 stream.
    """
    if not req.text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    audio_bytes = await SpeechService.synthesize_speech(req.text)
    if not audio_bytes:
        # Client side should fallback to Web Speech API
        return Response(status_code=204)

    return Response(content=audio_bytes, media_type="audio/mpeg")
