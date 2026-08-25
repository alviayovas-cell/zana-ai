"""
profile.py — User Profile REST API (Phase 6A).

Endpoints:
  GET  /api/profile?user_id=... — Get profile
  POST /api/profile             — Update profile
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.profile_service import profile_service

router = APIRouter(prefix="/profile", tags=["Profile"])


class UpdateProfileRequest(BaseModel):
    user_id: str = "default-user"
    display_name: Optional[str] = None
    preferred_language: Optional[str] = None
    timezone: Optional[str] = None
    tts_enabled: Optional[bool] = None
    wake_word_enabled: Optional[bool] = None
    music_preferences: Optional[Dict[str, Any]] = None
    assistant_preferences: Optional[Dict[str, Any]] = None


@router.get("")
async def get_profile(user_id: str = Query(default="default-user")):
    """Get personal user profile."""
    prof = await profile_service.get_profile(user_id)
    return prof.to_dict()


@router.post("")
async def update_profile(req: UpdateProfileRequest):
    """Update personal user profile."""
    updates = req.dict(exclude_unset=True)
    user_id = updates.pop("user_id", "default-user")
    updated_prof = await profile_service.update_profile(user_id, updates)
    return updated_prof.to_dict()
