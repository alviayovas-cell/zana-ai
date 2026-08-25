"""
profile_service.py — Personal User Profiles Service for Zana (Phase 6A).

Manages user profile preferences:
  - user_id / session_id
  - display_name
  - preferred_language ("en", "ta", "hi")
  - timezone
  - tts_enabled
  - wake_word_enabled
  - music_preferences (genres, artists)
  - assistant_preferences

Persisted in MongoDB `profiles` collection with graceful in-memory fallback.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

from app.core.logging_config import logger
from app.services.mongo_service import mongo_service


@dataclass
class UserProfile:
    user_id: str
    display_name: str = "Music Enthusiast"
    preferred_language: str = "en"
    timezone: str = "UTC"
    tts_enabled: bool = False
    wake_word_enabled: bool = True
    music_preferences: Dict[str, Any] = field(default_factory=dict)
    assistant_preferences: Dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProfileService:
    """Manages user profile loading, saving, and defaults."""

    def __init__(self) -> None:
        self._cache: Dict[str, UserProfile] = {}

    async def get_profile(self, user_id: str) -> UserProfile:
        """Get profile for user_id from cache or MongoDB."""
        if user_id in self._cache:
            return self._cache[user_id]

        if mongo_service.is_connected() and mongo_service._db is not None:
            try:
                doc = await mongo_service._db.profiles.find_one({"user_id": user_id})
                if doc:
                    profile = UserProfile(
                        user_id=doc["user_id"],
                        display_name=doc.get("display_name", "Music Enthusiast"),
                        preferred_language=doc.get("preferred_language", "en"),
                        timezone=doc.get("timezone", "UTC"),
                        tts_enabled=doc.get("tts_enabled", False),
                        wake_word_enabled=doc.get("wake_word_enabled", True),
                        music_preferences=doc.get("music_preferences", {}),
                        assistant_preferences=doc.get("assistant_preferences", {}),
                        updated_at=doc.get("updated_at", time.time()),
                    )
                    self._cache[user_id] = profile
                    return profile
            except Exception as exc:
                logger.warning(f"[PROFILE] Error loading profile from MongoDB: {exc}")

        # Default fallback profile
        prof = UserProfile(user_id=user_id)
        self._cache[user_id] = prof
        return prof

    async def update_profile(self, user_id: str, updates: Dict[str, Any]) -> UserProfile:
        """Update profile fields and save to MongoDB."""
        prof = await self.get_profile(user_id)

        if "display_name" in updates:
            prof.display_name = str(updates["display_name"])
        if "preferred_language" in updates:
            prof.preferred_language = str(updates["preferred_language"])
        if "timezone" in updates:
            prof.timezone = str(updates["timezone"])
        if "tts_enabled" in updates:
            prof.tts_enabled = bool(updates["tts_enabled"])
        if "wake_word_enabled" in updates:
            prof.wake_word_enabled = bool(updates["wake_word_enabled"])
        if "music_preferences" in updates and isinstance(updates["music_preferences"], dict):
            prof.music_preferences.update(updates["music_preferences"])
        if "assistant_preferences" in updates and isinstance(updates["assistant_preferences"], dict):
            prof.assistant_preferences.update(updates["assistant_preferences"])

        prof.updated_at = time.time()
        self._cache[user_id] = prof

        if mongo_service.is_connected() and mongo_service._db is not None:
            try:
                await mongo_service._db.profiles.update_one(
                    {"user_id": user_id},
                    {"$set": prof.to_dict()},
                    upsert=True,
                )
                logger.info(f"[PROFILE] Saved updated profile for user '{user_id}' to MongoDB")
            except Exception as exc:
                logger.warning(f"[PROFILE] Error saving profile to MongoDB: {exc}")

        return prof


# Singleton instance
profile_service = ProfileService()
