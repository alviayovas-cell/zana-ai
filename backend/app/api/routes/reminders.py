"""
reminders.py — Proactive Reminders REST API (Phase 6A).

Endpoints:
  GET    /api/reminders           — List reminders for user
  POST   /api/reminders           — Create reminder
  DELETE /api/reminders/{id}      — Delete reminder
  GET    /api/reminders/due       — Check due reminders
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.reminder_service import reminder_service

router = APIRouter(prefix="/reminders", tags=["Reminders"])


class CreateReminderRequest(BaseModel):
    user_id: str = "default-user"
    message: str
    delay_seconds: float = 0.0
    scheduled_at: Optional[float] = None
    recurrence: str = "none"


@router.get("")
async def list_reminders(user_id: str = Query(default="default-user"), status: Optional[str] = None):
    """List reminders for a user."""
    items = await reminder_service.get_reminders(user_id=user_id, status=status)
    return {"reminders": [r.to_dict() for r in items], "count": len(items)}


@router.post("")
async def create_reminder(req: CreateReminderRequest):
    """Create a new reminder."""
    item = await reminder_service.create_reminder(
        user_id=req.user_id,
        message=req.message,
        delay_seconds=req.delay_seconds,
        scheduled_at=req.scheduled_at,
        recurrence=req.recurrence,
    )
    return {"success": True, "reminder": item.to_dict()}


@router.delete("/{reminder_id}")
async def delete_reminder(reminder_id: str, user_id: str = Query(default="default-user")):
    """Delete a reminder."""
    deleted = await reminder_service.delete_reminder(user_id=user_id, reminder_id=reminder_id)
    return {"success": deleted}


@router.get("/due")
async def get_due_reminders():
    """Poll for due reminders."""
    due = await reminder_service.check_due_reminders()
    return {"due": [r.to_dict() for r in due], "count": len(due)}
