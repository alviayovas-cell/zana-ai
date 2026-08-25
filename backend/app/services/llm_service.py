"""
llm_service.py — Unified LLM integration service for Zana AI Brain.

Responsibilities:
  - Multi-provider support (OpenAI and Groq)
  - Auto-resolution based on configured API keys in environment variables
  - Structured JSON completion generation for intent classification & tool calling
  - Conversational text completion generation
  - Timeout, retry, and exception safety (never crashes the app)

Security:
  - All API keys are loaded strictly from backend settings (.env)
  - Never exposes API keys to client/frontend
"""
import json
import re
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.core.logging_config import logger


OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMService:
    """
    Backend service providing LLM reasoning and language understanding
    to the Zana AI Brain.
    """

    def is_configured(self) -> bool:
        """Return True if at least one LLM provider has an API key configured."""
        return bool(settings.OPENAI_API_KEY or settings.GROQ_API_KEY)

    def get_provider_info(self) -> Dict[str, Any]:
        """Return metadata about the currently active LLM provider."""
        pref = settings.LLM_PROVIDER.lower()
        if (pref in ("openai", "auto")) and settings.OPENAI_API_KEY:
            return {
                "provider": "openai",
                "model": settings.OPENAI_MODEL,
                "configured": True,
            }
        elif (pref in ("groq", "auto")) and settings.GROQ_API_KEY:
            return {
                "provider": "groq",
                "model": settings.GROQ_MODEL,
                "configured": True,
            }
        return {
            "provider": "fallback",
            "model": "rule-based-engine",
            "configured": False,
        }

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> Optional[Dict[str, Any]]:
        """
        Send a prompt to the LLM and return parsed structured JSON output.

        Returns None if no key is configured or if the LLM request fails.
        """
        info = self.get_provider_info()
        provider = info["provider"]

        if provider == "fallback":
            logger.debug("[LLM-SERVICE] No LLM API key configured — returning None for JSON completion.")
            return None

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        if provider == "openai":
            url = OPENAI_API_URL
            api_key = settings.OPENAI_API_KEY
            model = settings.OPENAI_MODEL
        else:  # groq
            url = GROQ_API_URL
            api_key = settings.GROQ_API_KEY
            model = settings.GROQ_MODEL

        logger.info(f"[LLM-SERVICE] Requesting JSON completion via {provider} ({model})")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 350,
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            if resp.status_code != 200:
                logger.error(f"[LLM-SERVICE] {provider} LLM error {resp.status_code}: {resp.text[:300]}")
                return None

            raw_text = resp.json()["choices"][0]["message"]["content"]
            return self._clean_and_parse_json(raw_text)

        except httpx.TimeoutException:
            logger.error(f"[LLM-SERVICE] {provider} request timed out.")
            return None
        except Exception as exc:
            logger.error(f"[LLM-SERVICE] Exception during LLM JSON call: {exc}", exc_info=True)
            return None

    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
    ) -> Optional[str]:
        """
        Generate a conversational text completion from a list of message dicts.

        Returns None if request fails or no LLM provider is available.
        """
        info = self.get_provider_info()
        provider = info["provider"]

        if provider == "fallback":
            return None

        if provider == "openai":
            url = OPENAI_API_URL
            api_key = settings.OPENAI_API_KEY
            model = settings.OPENAI_MODEL
        else:
            url = GROQ_API_URL
            api_key = settings.GROQ_API_KEY
            model = settings.GROQ_MODEL

        logger.info(f"[LLM-SERVICE] Requesting text completion via {provider} ({model})")

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": 200,
                    },
                )

            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"[LLM-SERVICE] {provider} text error {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as exc:
            logger.error(f"[LLM-SERVICE] Text generation error: {exc}")
            return None

    def _clean_and_parse_json(self, raw: str) -> Optional[Dict[str, Any]]:
        """Safely parse JSON from raw LLM output."""
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            logger.warning(f"[LLM-SERVICE] Failed to parse JSON: {cleaned[:150]}")
            return None


# Singleton instance
llm_service = LLMService()
