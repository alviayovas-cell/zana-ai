import io
import os
import time
from abc import ABC, abstractmethod
from typing import Optional
import httpx

from app.core.config import settings
from app.core.logging_config import logger


class SpeechToTextProvider(ABC):
    """Abstract interface for Speech-to-Text providers."""

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """Transcribe raw audio bytes to text transcript."""
        pass


class GroqWhisperProvider(SpeechToTextProvider):
    """Ultra-fast Whisper STT via Groq Cloud API (~200ms latency)."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/audio/transcriptions"

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {
            "file": (filename, audio_bytes, "audio/webm"),
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

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {
            "file": (filename, audio_bytes, "audio/webm"),
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


class FallbackSTTProvider(SpeechToTextProvider):
    """
    Fallback provider when no cloud API keys are provided.
    Logs warning and provides helpful diagnostic message.
    """

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        logger.warning(
            "[STT:Fallback] Audio received (%d bytes), but no GROQ_API_KEY or OPENAI_API_KEY configured.",
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
            logger.info("[STT] Using Fallback STT Provider (Configure GROQ_API_KEY or OPENAI_API_KEY in .env for full cloud Whisper transcription).")
            self._provider = FallbackSTTProvider()

    def set_provider(self, provider: SpeechToTextProvider):
        self._provider = provider

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        if not self._provider:
            self._init_provider()
        
        start_time = time.time()
        transcript = await self._provider.transcribe(audio_bytes, filename)
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"[STT] Transcribed in {duration_ms:.1f}ms: '{transcript}'")
        return transcript


stt_service = STTService()
