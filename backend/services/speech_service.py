import os
import io
import httpx
from dotenv import load_dotenv

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") # Rachel (warm voice)

class SpeechService:
    """
    Speech-to-Text (STT) and Text-to-Speech (TTS) engine.
    Integrates Deepgram and ElevenLabs with client-side Web Speech fallbacks.
    """

    @classmethod
    async def transcribe_audio(cls, audio_bytes: bytes, content_type: str = "audio/webm") -> str:
        """
        Transcribes voice recording to text using Deepgram API.
        """
        if not DEEPGRAM_API_KEY or DEEPGRAM_API_KEY == "your_deepgram_api_key_here":
            return ""

        url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true"
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": content_type
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, content=audio_bytes)
            if response.status_code == 200:
                data = response.json()
                transcript = (
                    data.get("results", {})
                    .get("channels", [{}])[0]
                    .get("alternatives", [{}])[0]
                    .get("transcript", "")
                )
                return transcript
            else:
                print(f"[SpeechService] Deepgram error {response.status_code}: {response.text}")
                return ""

    @classmethod
    async def synthesize_speech(cls, text: str) -> bytes:
        """
        Synthesizes empathetic speech audio from text using ElevenLabs API.
        """
        if not ELEVENLABS_API_KEY or ELEVENLABS_API_KEY == "your_elevenlabs_api_key_here":
            return b""

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.3,
                "use_speaker_boost": True
            }
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.content
            else:
                print(f"[SpeechService] ElevenLabs error {response.status_code}: {response.text}")
                return b""
