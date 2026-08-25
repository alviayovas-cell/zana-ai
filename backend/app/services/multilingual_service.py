"""
multilingual_service.py — Multilingual Voice & Intent Router for Zana (Phase 6A).

Supported Languages:
  - English ("en")
  - Tamil ("ta")
  - Hindi ("hi")

Responsibilities:
  - Detect input language from script/text heuristics
  - Map STT language codes to SpeechRecognition/Whisper models
  - Select localized TTS voice rates and parameters
"""
from __future__ import annotations

import re
from typing import Any, Dict

from app.core.logging_config import logger


class MultilingualService:
    """Detects and routes language settings for STT, Brain, and TTS."""

    # Tamil script range: \u0B80-\u0BFF
    _TAMIL_RE = re.compile(r"[\u0B80-\u0BFF]")
    # Devanagari (Hindi) script range: \u0900-\u097F
    _HINDI_RE = re.compile(r"[\u0900-\u097F]")

    def detect_language(self, text: str, fallback_lang: str = "en") -> str:
        """
        Detect input language. Returns 'ta' for Tamil, 'hi' for Hindi, else 'en'.
        """
        if self._TAMIL_RE.search(text):
            logger.info(f"[MULTILINGUAL] Detected Tamil input script")
            return "ta"
        if self._HINDI_RE.search(text):
            logger.info(f"[MULTILINGUAL] Detected Hindi input script")
            return "hi"

        lower = text.lower()
        # Heuristic keywords for transliterated Hindi/Tamil
        if any(w in lower for w in ["paattu", "padal", "patna", "tamil", "vanakkam", "epdi"]):
            return "ta"
        if any(w in lower for w in ["gaana", "geet", "namaste", "kaise", "hindi"]):
            return "hi"

        return fallback_lang

    def get_stt_params(self, lang: str) -> Dict[str, Any]:
        """Return STT language parameters for SpeechRecognition/Whisper."""
        if lang == "ta":
            return {"language": "ta-IN", "whisper_lang": "ta"}
        elif lang == "hi":
            return {"language": "hi-IN", "whisper_lang": "hi"}
        return {"language": "en-US", "whisper_lang": "en"}

    def get_tts_params(self, lang: str) -> Dict[str, Any]:
        """Return Web SpeechSynthesis parameters for target language."""
        if lang == "ta":
            return {"lang": "ta-IN", "rate": 0.95}
        elif lang == "hi":
            return {"lang": "hi-IN", "rate": 0.95}
        return {"lang": "en-US", "rate": 1.0}


# Singleton instance
multilingual_service = MultilingualService()
