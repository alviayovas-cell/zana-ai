"""
memory.py — REST API routes for Zana user memory management (Phase 5).

Endpoints:
  GET    /api/memory         — List all memories for a session
  POST   /api/memory         — Save an explicit memory
  DELETE /api/memory/{id}    — Delete a specific memory
  DELETE /api/memory         — Clear all memories for a session
"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.assistant.brain.memory_store import memory_store
from app.core.logging_config import logger

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryItem(BaseModel):
    id: Optional[str] = None
    session_id: str
    content: str
    category: Optional[str] = "general"
    created_at: Optional[float] = None


class SaveMemoryRequest(BaseModel):
    session_id: str
    content: str
    category: Optional[str] = "general"


class MemoryListResponse(BaseModel):
    session_id: str
    memories: List[MemoryItem]
    count: int
    source: str = "memory_store"


@router.get("", response_model=MemoryListResponse)
async def list_memories(session_id: str = Query(default="dev-session")):
    """List all long-term memories for a session."""
    try:
        mems = await memory_store.get_memories_list(session_id)
        return MemoryListResponse(
            session_id=session_id,
            memories=[
                MemoryItem(
                    id=m.get("id"),
                    session_id=m["session_id"],
                    content=m["content"],
                    category=m.get("category", "general"),
                    created_at=m.get("created_at"),
                )
                for m in mems
            ],
            count=len(mems),
        )
    except Exception as exc:
        logger.error(f"[MEMORY API] Error listing memories: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("", response_model=dict)
async def save_memory(req: SaveMemoryRequest):
    """Save an explicit user memory."""
    try:
        logger.info(f"[MEMORY API] Saving explicit memory for session '{req.session_id}': {req.content!r}")
        saved = await memory_store.save_explicit_memory(req.session_id, req.content)
        if saved:
            return {"success": True, "message": "Memory saved.", "content": req.content}
        return {"success": False, "message": "Memory could not be saved."}
    except Exception as exc:
        logger.error(f"[MEMORY API] Error saving memory: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{memory_id}", response_model=dict)
async def delete_memory(memory_id: str, session_id: str = Query(default="dev-session")):
    """Delete a specific memory by ID."""
    try:
        deleted = await memory_store.delete_memory(session_id, memory_id)
        return {"success": deleted, "message": "Memory deleted." if deleted else "Memory not found."}
    except Exception as exc:
        logger.error(f"[MEMORY API] Error deleting memory: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("", response_model=dict)
async def clear_memories(session_id: str = Query(default="dev-session")):
    """Clear all long-term memories for a session."""
    try:
        await memory_store.clear(session_id)
        return {"success": True, "message": f"All memories cleared for session '{session_id}'."}
    except Exception as exc:
        logger.error(f"[MEMORY API] Error clearing memories: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
