"""
mongo_service.py — MongoDB Service for Zana (Phase 5).

Manages persistent storage for:
  - Conversations history (`conversations` collection)
  - Long-term user memory & preferences (`memories` collection)

Features:
  - Async operations using Motor
  - Automatic index setup
  - Graceful degraded fallback mode if MongoDB server is offline or URI is invalid (app never crashes)
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.logging_config import logger

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False
    AsyncIOMotorClient = None


class MongoService:
    """
    MongoDB service adapter for Zana. Provides access to `conversations`
    and `memories` collections with automatic connection testing and fallback.
    """

    def __init__(self) -> None:
        self._client: Optional[Any] = None
        self._db: Optional[Any] = None
        self._is_connected: bool = False
        self._checked_connection: bool = False

    async def connect(self) -> bool:
        """Attempt async connection to MongoDB."""
        if not HAS_MOTOR:
            logger.warning("[MEMORY] Motor package not installed — operating in degraded in-memory mode.")
            self._is_connected = False
            return False

        if not settings.MONGODB_URI:
            logger.info("[MEMORY] No MONGODB_URI configured — operating in degraded in-memory mode.")
            self._is_connected = False
            return False

        try:
            logger.info(f"[MEMORY] Connecting to MongoDB ({settings.MONGODB_DB_NAME})...")
            self._client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=2500,
            )
            self._db = self._client[settings.MONGODB_DB_NAME]
            # Ping database to confirm connection
            await self._client.admin.command("ping")
            self._is_connected = True
            logger.info(f"[MEMORY] Connected to MongoDB Atlas/DB: '{settings.MONGODB_DB_NAME}' ✅")

            # Setup indexes
            await self._setup_indexes()
            return True
        except Exception as exc:
            logger.warning(f"[MEMORY] MongoDB connection failed: {exc} — degraded in-memory mode active.")
            self._is_connected = False
            self._client = None
            self._db = None
            return False

    async def _setup_indexes(self) -> None:
        """Create indexes on collections for fast lookup."""
        if not self._is_connected or self._db is None:
            return
        try:
            await self._db.conversations.create_index([("session_id", 1), ("created_at", -1)])
            await self._db.memories.create_index([("session_id", 1), ("key", 1)], unique=False)
            await self._db.music_searches.create_index([("session_id", 1), ("created_at", -1)])
            logger.info("[MEMORY] MongoDB collection indexes verified.")
        except Exception as exc:
            logger.warning(f"[MEMORY] Index creation warning: {exc}")

    def is_connected(self) -> bool:
        return self._is_connected

    # ── Music Search History Persistence ──────────────────────────────────────

    async def save_music_search(
        self,
        session_id: str,
        query: str,
        track_id: Optional[str] = None,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        spotify_url: Optional[str] = None,
    ) -> None:
        """Save a music search record to MongoDB."""
        if not self._is_connected or self._db is None:
            return
        try:
            doc = {
                "session_id": session_id,
                "query": query,
                "track_id": track_id,
                "title": title,
                "artist": artist,
                "album": album,
                "spotify_url": spotify_url,
                "created_at": time.time(),
            }
            await self._db.music_searches.insert_one(doc)
            logger.debug(f"[MEMORY] Saved music search for '{query}' (session={session_id}) to MongoDB")
        except Exception as exc:
            logger.warning(f"[MEMORY] Error saving music search to MongoDB: {exc}")

    def save_music_search_background(
        self,
        session_id: str,
        query: str,
        track_id: Optional[str] = None,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        spotify_url: Optional[str] = None,
    ) -> None:
        """Persist music search record without blocking the API response."""
        if not self._is_connected or self._db is None:
            return
        asyncio.create_task(
            self.save_music_search(session_id, query, track_id, title, artist, album, spotify_url)
        )

    # ── Conversations Persistence ──────────────────────────────────────────────

    async def save_conversation_turn(
        self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Save a single conversation turn to MongoDB."""
        if not self._is_connected or self._db is None:
            return
        try:
            doc = {
                "session_id": session_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
                "created_at": time.time(),
            }
            await self._db.conversations.insert_one(doc)
            logger.debug(f"[MEMORY] Saved conversation turn for session '{session_id}' to MongoDB")
        except Exception as exc:
            logger.warning(f"[MEMORY] Error saving conversation turn to MongoDB: {exc}")

    async def get_recent_conversations(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent conversation turns for a session from MongoDB."""
        if not self._is_connected or self._db is None:
            return []
        try:
            cursor = self._db.conversations.find(
                {"session_id": session_id}
            ).sort("created_at", -1).limit(limit)
            items = await cursor.to_list(length=limit)
            items.reverse()
            return [{"role": item["role"], "content": item["content"]} for item in items]
        except Exception as exc:
            logger.warning(f"[MEMORY] Error fetching conversations from MongoDB: {exc}")
            return []

    # ── Long-Term User Memories Persistence ───────────────────────────────────

    async def save_memory(
        self,
        session_id: str,
        content: str,
        category: str = "general",
        key: Optional[str] = None,
        value: Optional[str] = None,
    ) -> Optional[str]:
        """Save a long-term user memory to MongoDB."""
        if not self._is_connected or self._db is None:
            return None
        try:
            doc = {
                "session_id": session_id,
                "content": content,
                "category": category,
                "key": key or category,
                "value": value or content,
                "created_at": time.time(),
                "updated_at": time.time(),
            }
            res = await self._db.memories.insert_one(doc)
            mem_id = str(res.inserted_id)
            logger.info(f"[MEMORY] Saved memory to MongoDB: id={mem_id}, category={category!r}, content={content!r}")
            return mem_id
        except Exception as exc:
            logger.warning(f"[MEMORY] Error saving memory to MongoDB: {exc}")
            return None

    def save_memory_background(
        self,
        session_id: str,
        content: str,
        category: str = "general",
        key: Optional[str] = None,
        value: Optional[str] = None,
    ) -> None:
        """Persist a memory without blocking the response that created it."""
        if not self._is_connected or self._db is None:
            return
        asyncio.create_task(self.save_memory(session_id, content, category, key, value))

    async def get_memories(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve all long-term memories for a session from MongoDB."""
        if not self._is_connected or self._db is None:
            return []
        try:
            cursor = self._db.memories.find({"session_id": session_id}).sort("created_at", -1)
            docs = await cursor.to_list(length=100)
            return [
                {
                    "id": str(d["_id"]),
                    "session_id": d["session_id"],
                    "content": d["content"],
                    "category": d.get("category", "general"),
                    "key": d.get("key"),
                    "value": d.get("value"),
                    "created_at": d.get("created_at"),
                }
                for d in docs
            ]
        except Exception as exc:
            logger.warning(f"[MEMORY] Error fetching memories from MongoDB: {exc}")
            return []

    async def delete_memory(self, session_id: str, memory_id: str) -> bool:
        """Delete a specific memory from MongoDB."""
        if not self._is_connected or self._db is None:
            return False
        try:
            from bson import ObjectId
            res = await self._db.memories.delete_one({"session_id": session_id, "_id": ObjectId(memory_id)})
            return res.deleted_count > 0
        except Exception as exc:
            logger.warning(f"[MEMORY] Error deleting memory from MongoDB: {exc}")
            return False

    async def clear_all_memories(self, session_id: str) -> bool:
        """Clear all memories for a session from MongoDB."""
        if not self._is_connected or self._db is None:
            return False
        try:
            res = await self._db.memories.delete_many({"session_id": session_id})
            logger.info(f"[MEMORY] Cleared {res.deleted_count} memories for session '{session_id}' in MongoDB.")
            return True
        except Exception as exc:
            logger.warning(f"[MEMORY] Error clearing memories in MongoDB: {exc}")
            return False


# Singleton instance
mongo_service = MongoService()
