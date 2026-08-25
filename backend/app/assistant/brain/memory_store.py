"""
memory_store.py — Long-term preference memory for Zana AI Brain (Phase 5).

Stores user preferences and learned facts across conversations.
Integrates with MongoDB (via mongo_service) for persistent storage while
maintaining in-memory caching for zero-latency lookups and degraded fallback.

Features:
  - Explicit Memory Save: "Remember that I like Tamil songs"
  - Opportunistic Memory Save: auto-saves preferred artists/genres from successful plays
  - Relevant Context Retrieval: retrieves matching memories for session & prompt
  - Controllable: full CRUD (get, save, delete, clear)
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from app.core.logging_config import logger
from app.services.mongo_service import mongo_service


@dataclass
class UserMemory:
    """Long-term preferences for a user/session."""

    session_id: str

    # Music preferences
    preferred_genres: List[str] = field(default_factory=list)
    preferred_artists: List[str] = field(default_factory=list)
    preferred_languages: List[str] = field(default_factory=list)

    # General preferences / facts
    facts: Dict[str, str] = field(default_factory=dict)

    # Metadata
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def add_preferred_artist(self, artist: str) -> None:
        if artist and artist not in self.preferred_artists:
            self.preferred_artists.append(artist)
            self.updated_at = time.time()
            logger.debug(f"[MEMORY] Added artist preference: {artist}")

    def add_preferred_genre(self, genre: str) -> None:
        if genre and genre not in self.preferred_genres:
            self.preferred_genres.append(genre)
            self.updated_at = time.time()
            logger.debug(f"[MEMORY] Added genre preference: {genre}")

    def add_preferred_language(self, lang: str) -> None:
        if lang and lang not in self.preferred_languages:
            self.preferred_languages.append(lang)
            self.updated_at = time.time()
            logger.debug(f"[MEMORY] Added language preference: {lang}")

    def add_fact(self, key: str, value: str) -> None:
        self.facts[key] = value
        self.updated_at = time.time()

    def to_context_string(self) -> str:
        """
        Return a compact natural-language summary for injection into LLM prompts.
        Only includes non-empty fields.
        """
        lines = []
        if self.preferred_artists:
            lines.append(f"User's favourite artists: {', '.join(self.preferred_artists[:5])}")
        if self.preferred_genres:
            lines.append(f"User's preferred genres: {', '.join(self.preferred_genres[:5])}")
        if self.preferred_languages:
            lines.append(f"User's preferred music languages: {', '.join(self.preferred_languages[:3])}")
        for k, v in list(self.facts.items())[:5]:
            lines.append(f"{k}: {v}")
        return "\n".join(lines) if lines else ""

    def is_empty(self) -> bool:
        return (
            not self.preferred_artists
            and not self.preferred_genres
            and not self.preferred_languages
            and not self.facts
        )


# Regex patterns for explicit user memory statements
_EXPLICIT_MEMORY_RE = re.compile(
    r"(?:remember\s+(?:that\s+)?|i\s+like\s+|i\s+love\s+|my\s+favorite\s+(?:artist|genre|language|song)\s+is\s+)(.+)",
    re.IGNORECASE,
)
_LANGUAGE_RE = re.compile(r"\b(tamil|hindi|english|telugu|punjabi|kannada|malayalam|spanish|korean|japanese)\b", re.IGNORECASE)


class MemoryStore:
    """
    Persistent & cached memory store.

    Interface:
      - get_or_create(session_id) -> UserMemory
      - save_explicit_memory(session_id, text) -> bool
      - retrieve_relevant_memories(session_id, query) -> str
      - extract_and_store(...)
      - clear(session_id)
    """

    def __init__(self) -> None:
        self._store: Dict[str, UserMemory] = {}

    def get_or_create(self, session_id: str) -> UserMemory:
        if session_id not in self._store:
            self._store[session_id] = UserMemory(session_id=session_id)
        return self._store[session_id]

    def get(self, session_id: str) -> Optional[UserMemory]:
        return self._store.get(session_id)

    async def save_explicit_memory(self, session_id: str, content: str) -> bool:
        """
        Explicitly store a memory item (e.g. "Remember that I like Tamil songs").
        Saves to MongoDB and updates in-memory cache.
        """
        mem = self.get_or_create(session_id)

        lang_match = _LANGUAGE_RE.search(content)
        if lang_match:
            lang = lang_match.group(1).title()
            mem.add_preferred_language(lang)

        # Parse genre/artist/fact
        if "artist" in content.lower():
            mem.add_fact("Favorite Artist", content)
        elif "genre" in content.lower() or "music" in content.lower():
            mem.add_fact("Music Preference", content)
        else:
            mem.add_fact("User Fact", content)

        # Persist to MongoDB if available
        if mongo_service.is_connected():
            await mongo_service.save_memory(
                session_id=session_id,
                content=content,
                category="user_preference",
                key="preference",
                value=content,
            )

        logger.info(f"[MEMORY] Explicit memory saved for session '{session_id}': {content!r}")
        return True

    async def get_memories_list(self, session_id: str) -> List[Dict[str, Any]]:
        """Return list of stored memory dicts for API / UI."""
        if mongo_service.is_connected():
            mongo_mems = await mongo_service.get_memories(session_id)
            if mongo_mems:
                return mongo_mems

        # Fallback from in-memory cache
        mem = self.get(session_id)
        if not mem or mem.is_empty():
            return []

        res = []
        for a in mem.preferred_artists:
            res.append({"id": f"artist-{a}", "session_id": session_id, "category": "artist", "content": f"Preferred artist: {a}"})
        for g in mem.preferred_genres:
            res.append({"id": f"genre-{g}", "session_id": session_id, "category": "genre", "content": f"Preferred genre: {g}"})
        for l in mem.preferred_languages:
            res.append({"id": f"lang-{l}", "session_id": session_id, "category": "language", "content": f"Preferred language: {l}"})
        for k, v in mem.facts.items():
            res.append({"id": f"fact-{k}", "session_id": session_id, "category": "fact", "content": f"{k}: {v}"})
        return res

    async def delete_memory(self, session_id: str, memory_id: str) -> bool:
        """Delete a specific memory by ID."""
        if mongo_service.is_connected():
            await mongo_service.delete_memory(session_id, memory_id)
        # Clear in-memory as well
        self.clear(session_id)
        return True

    async def clear(self, session_id: str) -> None:
        """Clear all memories for a session."""
        if session_id in self._store:
            del self._store[session_id]

        if mongo_service.is_connected():
            await mongo_service.clear_all_memories(session_id)

        logger.info(f"[MEMORY] Cleared all memories for session: {session_id}")

    def extract_and_store(
        self,
        session_id: str,
        intent: str,
        query: str,
        artist: Optional[str] = None,
        genre: Optional[str] = None,
    ) -> None:
        """
        Opportunistically learn preferences from successful actions.
        """
        mem = self.get_or_create(session_id)

        if artist and intent in ("music_search_play", "music_play"):
            mem.add_preferred_artist(artist)

        if genre and intent in ("music_search_play", "music_play"):
            mem.add_preferred_genre(genre)


# Singleton instance
memory_store = MemoryStore()
