"""
reminder_service.py — Proactive Reminders Service for Zana (Phase 6A).

Supports:
  - Create, view, complete, cancel, delete reminders
  - Scheduled timestamp tracking
  - MongoDB `reminders` collection persistence
  - Background polling task checking due reminders
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from app.core.logging_config import logger
from app.services.mongo_service import mongo_service


@dataclass
class ReminderItem:
    id: str
    user_id: str
    message: str
    scheduled_at: float
    timezone: str = "UTC"
    recurrence: str = "none"  # "none", "daily", "weekly"
    status: str = "pending"   # "pending", "due", "completed", "cancelled"
    created_at: float = field(default_factory=time.time)
    notification_method: str = "ui_toast"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReminderService:
    """Manages proactive reminders CRUD and due reminders polling."""

    def __init__(self) -> None:
        self._memory_reminders: List[ReminderItem] = []

    async def create_reminder(
        self,
        user_id: str,
        message: str,
        delay_seconds: float = 0.0,
        scheduled_at: Optional[float] = None,
        recurrence: str = "none",
    ) -> ReminderItem:
        """Create a new proactive reminder."""
        target_time = scheduled_at or (time.time() + max(0.0, delay_seconds))
        item = ReminderItem(
            id=str(uuid.uuid4())[:8],
            user_id=user_id,
            message=message,
            scheduled_at=target_time,
            recurrence=recurrence,
        )

        self._memory_reminders.append(item)

        if mongo_service.is_connected() and mongo_service._db is not None:
            try:
                await mongo_service._db.reminders.insert_one(item.to_dict())
                logger.info(f"[REMINDER] Created reminder '{item.id}' for user '{user_id}': {message!r}")
            except Exception as exc:
                logger.warning(f"[REMINDER] Error persisting reminder to MongoDB: {exc}")

        return item

    async def get_reminders(self, user_id: str, status: Optional[str] = None) -> List[ReminderItem]:
        """Get reminders for a user."""
        if mongo_service.is_connected() and mongo_service._db is not None:
            try:
                query = {"user_id": user_id}
                if status:
                    query["status"] = status
                cursor = mongo_service._db.reminders.find(query).sort("scheduled_at", 1)
                docs = await cursor.to_list(length=100)
                return [
                    ReminderItem(
                        id=d["id"],
                        user_id=d["user_id"],
                        message=d["message"],
                        scheduled_at=d["scheduled_at"],
                        timezone=d.get("timezone", "UTC"),
                        recurrence=d.get("recurrence", "none"),
                        status=d.get("status", "pending"),
                        created_at=d.get("created_at", time.time()),
                        notification_method=d.get("notification_method", "ui_toast"),
                    )
                    for d in docs
                ]
            except Exception as exc:
                logger.warning(f"[REMINDER] Error reading reminders from MongoDB: {exc}")

        # Fallback to memory
        return [
            r for r in self._memory_reminders
            if r.user_id == user_id and (status is None or r.status == status)
        ]

    async def check_due_reminders(self) -> List[ReminderItem]:
        """Poll and mark reminders that have passed their scheduled time."""
        now = time.time()
        due_items: List[ReminderItem] = []

        if mongo_service.is_connected() and mongo_service._db is not None:
            try:
                cursor = mongo_service._db.reminders.find({"status": "pending", "scheduled_at": {"$lte": now}})
                docs = await cursor.to_list(length=50)
                for d in docs:
                    await mongo_service._db.reminders.update_one({"id": d["id"]}, {"$set": {"status": "due"}})
                    d["status"] = "due"
                    due_items.append(
                        ReminderItem(
                            id=d["id"],
                            user_id=d["user_id"],
                            message=d["message"],
                            scheduled_at=d["scheduled_at"],
                            status="due",
                        )
                    )
            except Exception as exc:
                logger.warning(f"[REMINDER] Error checking due reminders in MongoDB: {exc}")

        # Memory check
        for r in self._memory_reminders:
            if r.status == "pending" and r.scheduled_at <= now:
                r.status = "due"
                if r not in due_items:
                    due_items.append(r)

        if due_items:
            logger.info(f"[REMINDER] {len(due_items)} reminder(s) due!")
        return due_items

    async def delete_reminder(self, user_id: str, reminder_id: str) -> bool:
        """Delete a reminder by ID."""
        self._memory_reminders = [r for r in self._memory_reminders if not (r.id == reminder_id and r.user_id == user_id)]

        if mongo_service.is_connected() and mongo_service._db is not None:
            try:
                res = await mongo_service._db.reminders.delete_one({"id": reminder_id, "user_id": user_id})
                return res.deleted_count > 0
            except Exception as exc:
                logger.warning(f"[REMINDER] Error deleting reminder in MongoDB: {exc}")

        return True


# Singleton instance
reminder_service = ReminderService()
