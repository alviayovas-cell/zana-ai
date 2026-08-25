"""
context_manager.py — Short-term conversation memory for Zana AI Brain.

Maintains per-session state including:
- Rolling message history (last 10 turns)
- Current intent
- Music context (last played artist/track/query)
- Conversation topic
- Turn count

All state is in-memory and scoped to the server process lifetime.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.core.logging_config import logger

# Maximum number of message turns to keep per session
MAX_HISTORY = 10
# Maximum number of sessions to hold in memory (LRU-like eviction)
MAX_SESSIONS = 1000
# Session TTL in seconds (2 hours idle)
SESSION_TTL_SECONDS = 7200


@dataclass
class ConversationContext:
    """All short-term state for a single user session."""

    session_id: str

    # Rolling conversation history: [{"role": "user"|"assistant", "content": "..."}]
    messages: List[Dict[str, str]] = field(default_factory=list)

    # Intent tracking
    current_intent: Optional[str] = None
    previous_intent: Optional[str] = None

    # Music state — updated whenever a music action succeeds
    last_played_query: Optional[str] = None       # e.g. "Arijit Singh"
    last_played_track: Optional[str] = None       # e.g. "Tum Hi Ho"
    last_played_artist: Optional[str] = None      # e.g. "Arijit Singh"
    last_played_genre: Optional[str] = None       # e.g. "relaxing"

    # General topic tracking
    current_topic: Optional[str] = None           # "music" | "general" | None

    # Metadata
    turn_count: int = 0
    last_active: float = field(default_factory=time.time)

    def add_user_message(self, content: str) -> None:
        """Append a user message to the rolling history."""
        self.messages.append({"role": "user", "content": content})
        if len(self.messages) > MAX_HISTORY:
            self.messages = self.messages[-MAX_HISTORY:]
        self.turn_count += 1
        self.last_active = time.time()
        # Non-blocking async save to MongoDB if connected
        from app.services.mongo_service import mongo_service
        import asyncio
        if mongo_service.is_connected():
            asyncio.create_task(mongo_service.save_conversation_turn(self.session_id, "user", content))

    def add_assistant_message(self, content: str) -> None:
        """Append an assistant message to the rolling history."""
        self.messages.append({"role": "assistant", "content": content})
        if len(self.messages) > MAX_HISTORY:
            self.messages = self.messages[-MAX_HISTORY:]
        self.last_active = time.time()
        # Non-blocking async save to MongoDB if connected
        from app.services.mongo_service import mongo_service
        import asyncio
        if mongo_service.is_connected():
            asyncio.create_task(mongo_service.save_conversation_turn(self.session_id, "assistant", content))

    def update_music_context(
        self,
        query: Optional[str] = None,
        track: Optional[str] = None,
        artist: Optional[str] = None,
        genre: Optional[str] = None,
    ) -> None:
        """Record the latest music play event."""
        if query is not None:
            self.last_played_query = query
        if track is not None:
            self.last_played_track = track
        if artist is not None:
            self.last_played_artist = artist
        if genre is not None:
            self.last_played_genre = genre
        self.current_topic = "music"

    def has_music_context(self) -> bool:
        """Return True if any music context is available."""
        return bool(
            self.last_played_query
            or self.last_played_track
            or self.last_played_artist
        )

    def get_music_summary(self) -> str:
        """Return a human-readable summary of current music context."""
        parts = []
        if self.last_played_track:
            parts.append(f"track='{self.last_played_track}'")
        if self.last_played_artist:
            parts.append(f"artist='{self.last_played_artist}'")
        if self.last_played_query:
            parts.append(f"query='{self.last_played_query}'")
        return ", ".join(parts) if parts else "none"

    def get_history_for_llm(self) -> List[Dict[str, str]]:
        """
        Return last N messages formatted for LLM context injection.
        Limits to last 6 turns (3 user + 3 assistant) to avoid bloat.
        """
        return self.messages[-6:]


class ContextManager:
    """
    Manages ConversationContext objects keyed by session_id.

    Thread-safety: Not needed for FastAPI async (single-threaded event loop).
    Eviction: Simple LRU by last_active timestamp when MAX_SESSIONS is reached.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, ConversationContext] = {}

    def get_or_create(self, session_id: str) -> ConversationContext:
        """Return existing context or create a fresh one."""
        if session_id not in self._sessions:
            logger.debug(f"[CONTEXT] Creating new session context: {session_id}")
            self._sessions[session_id] = ConversationContext(session_id=session_id)
            self._evict_if_needed()
        else:
            ctx = self._sessions[session_id]
            # Expire stale sessions
            if time.time() - ctx.last_active > SESSION_TTL_SECONDS:
                logger.debug(f"[CONTEXT] Session expired, resetting: {session_id}")
                self._sessions[session_id] = ConversationContext(session_id=session_id)
        return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[ConversationContext]:
        """Return context if it exists, else None."""
        return self._sessions.get(session_id)

    def clear_session(self, session_id: str) -> None:
        """Delete a session's context entirely."""
        self._sessions.pop(session_id, None)
        logger.info(f"[CONTEXT] Session cleared: {session_id}")

    def _evict_if_needed(self) -> None:
        """Remove oldest sessions when over the cap."""
        if len(self._sessions) > MAX_SESSIONS:
            oldest = sorted(
                self._sessions.items(),
                key=lambda kv: kv[1].last_active,
            )[:50]
            for sid, _ in oldest:
                del self._sessions[sid]
            logger.info(f"[CONTEXT] Evicted {len(oldest)} stale sessions.")

    def active_session_count(self) -> int:
        return len(self._sessions)


# Singleton instance
context_manager = ContextManager()
