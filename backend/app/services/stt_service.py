import io
import time
from abc import ABC, abstractmethod
from typing import Optional
import httpx
import speech_recognition as sr

from app.core.config import settings
from app.core.logging_config import logger


class SpeechToTextProvider(ABC):
    """Abstract interface for Speech-to-Text providers."""

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        """Transcribe raw audio bytes to text transcript."""
        pass


class GroqWhisperProvider(SpeechToTextProvider):
    """Ultra-fast Whisper STT via Groq Cloud API (~200ms latency)."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/audio/transcriptions"

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        mime = "audio/wav" if filename.endswith(".wav") else "audio/webm"
        files = {
            "file": (filename, audio_bytes, mime),
        }
        data = {
            "model": "whisper-large-v3-turbo",
            "response_format": "json",
            "language": "en",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(self.api_url, headers=headers, files=files, data=data)
            if resp.status_code != 200:
                logger.error(f"[STT:Groq] Error {resp.status_code}: {resp.text}")
                raise RuntimeError(f"Groq STT failed: {resp.text}")
            result = resp.json()
            return result.get("text", "").strip()


class OpenAIWhisperProvider(SpeechToTextProvider):
    """Whisper STT via OpenAI API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/audio/transcriptions"

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        mime = "audio/wav" if filename.endswith(".wav") else "audio/webm"
        files = {
            "file": (filename, audio_bytes, mime),
        }
        data = {
            "model": "whisper-1",
            "language": "en",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(self.api_url, headers=headers, files=files, data=data)
            if resp.status_code != 200:
                logger.error(f"[STT:OpenAI] Error {resp.status_code}: {resp.text}")
                raise RuntimeError(f"OpenAI STT failed: {resp.text}")
            result = resp.json()
            return result.get("text", "").strip()


class GoogleSpeechRecognitionProvider(SpeechToTextProvider):
    """
    Built-in free SpeechRecognition provider using Google Public STT.
    Requires no API keys and works natively from backend server for WAV audio.
    """

    def __init__(self):
        self.recognizer = sr.Recognizer()

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        try:
            buf = io.BytesIO(audio_bytes)
            with sr.AudioFile(buf) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data, language="en-US")
                return text.strip() if text else ""
        except sr.UnknownValueError:
            logger.info("[STT:Google] No intelligible speech detected.")
            return ""
        except sr.RequestError as e:
            logger.error(f"[STT:Google] Request error: {e}")
            return ""
        except Exception as e:
            logger.error(f"[STT:Google] Error reading audio file: {e}")
            return ""


class FallbackSTTProvider(SpeechToTextProvider):
    """Fallback provider."""

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        logger.warning(
            "[STT:Fallback] Audio received (%d bytes), no STT provider matched.",
            len(audio_bytes),
        )
        return ""


class STTService:
    """Service to resolve and execute the configured Speech-to-Text provider."""

    def __init__(self):
        self._provider: Optional[SpeechToTextProvider] = None
        self._init_provider()

    def _init_provider(self):
        pref = settings.STT_PROVIDER.lower()

        if (pref == "groq" or pref == "auto") and settings.GROQ_API_KEY:
            logger.info("[STT] Using Groq Whisper Provider.")
            self._provider = GroqWhisperProvider(settings.GROQ_API_KEY)
        elif (pref == "openai" or pref == "auto") and settings.OPENAI_API_KEY:
            logger.info("[STT] Using OpenAI Whisper Provider.")
            self._provider = OpenAIWhisperProvider(settings.OPENAI_API_KEY)
        else:
            logger.info("[STT] Using Free Google SpeechRecognition Provider (0 API keys required).")
            self._provider = GoogleSpeechRecognitionProvider()

    def set_provider(self, provider: SpeechToTextProvider):
        self._provider = provider

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        if not self._provider:
            self._init_provider()
        
        start_time = time.time()
        transcript = await self._provider.transcribe(audio_bytes, filename)
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"[STT] Transcribed in {duration_ms:.1f}ms: '{transcript}'")
        return transcript


stt_service = STTService()
