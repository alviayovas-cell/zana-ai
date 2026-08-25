"""
permission_manager.py — Central Permission & Approval System for Zana (Phase 6A).

Evaluates tool execution requests against defined risk levels and confirmation rules:
  - LOW: Automatic execution without user prompt (e.g. playback, volume, info)
  - MEDIUM: Requires confirmation if configured (e.g. creating/deleting reminders)
  - HIGH: Always requires explicit user confirmation (e.g. clear all memories, delete profile)

All decisions are recorded in an in-memory audit log and optional MongoDB collection.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.logging_config import logger


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PermissionStatus(str, Enum):
    ALLOWED = "ALLOWED"
    REQUIRES_CONFIRMATION = "REQUIRES_CONFIRMATION"
    DENIED = "DENIED"


@dataclass
class AuditRecord:
    timestamp: float
    session_id: str
    tool_name: str
    risk_level: RiskLevel
    status: PermissionStatus
    reason: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PermissionEvaluation:
    status: PermissionStatus
    tool_name: str
    risk_level: RiskLevel
    requires_confirmation: bool
    reason: str
    confirmation_prompt: Optional[str] = None


class PermissionManager:
    """
    Central permission evaluator and audit log store.
    """

    def __init__(self) -> None:
        self._audit_log: List[AuditRecord] = []
        # Custom risk overrides per tool_name if needed
        self._tool_risks: Dict[str, RiskLevel] = {}

    def evaluate(
        self,
        tool_name: str,
        session_id: str = "anonymous",
        risk_level: RiskLevel = RiskLevel.LOW,
        requires_confirmation: bool = False,
        arguments: Optional[Dict[str, Any]] = None,
        user_confirmed: bool = False,
    ) -> PermissionEvaluation:
        """
        Evaluate if a tool call can execute immediately or requires confirmation.
        """
        args = arguments or {}

        # 1. High risk always requires confirmation unless explicitly pre-confirmed by user
        if risk_level == RiskLevel.HIGH:
            if not user_confirmed:
                eval_res = PermissionEvaluation(
                    status=PermissionStatus.REQUIRES_CONFIRMATION,
                    tool_name=tool_name,
                    risk_level=risk_level,
                    requires_confirmation=True,
                    reason=f"High-risk tool '{tool_name}' requires explicit user confirmation.",
                    confirmation_prompt=f"Are you sure you want to execute '{tool_name}'?",
                )
                self._record_audit(session_id, tool_name, risk_level, PermissionStatus.REQUIRES_CONFIRMATION, "High-risk pending confirmation", args)
                return eval_res

        # 2. Medium risk requires confirmation if flagged
        elif risk_level == RiskLevel.MEDIUM and requires_confirmation and not user_confirmed:
            eval_res = PermissionEvaluation(
                status=PermissionStatus.REQUIRES_CONFIRMATION,
                tool_name=tool_name,
                risk_level=risk_level,
                requires_confirmation=True,
                reason=f"Medium-risk tool '{tool_name}' requires confirmation.",
                confirmation_prompt=f"Please confirm executing action '{tool_name}'.",
            )
            self._record_audit(session_id, tool_name, risk_level, PermissionStatus.REQUIRES_CONFIRMATION, "Medium-risk pending confirmation", args)
            return eval_res

        # 3. Allowed to execute
        eval_res = PermissionEvaluation(
            status=PermissionStatus.ALLOWED,
            tool_name=tool_name,
            risk_level=risk_level,
            requires_confirmation=False,
            reason="Action allowed by permission policy.",
        )
        self._record_audit(session_id, tool_name, risk_level, PermissionStatus.ALLOWED, "Allowed by policy", args)
        return eval_res

    def _record_audit(
        self,
        session_id: str,
        tool_name: str,
        risk_level: RiskLevel,
        status: PermissionStatus,
        reason: str,
        arguments: Dict[str, Any],
    ) -> None:
        rec = AuditRecord(
            timestamp=time.time(),
            session_id=session_id,
            tool_name=tool_name,
            risk_level=risk_level,
            status=status,
            reason=reason,
            arguments=arguments,
        )
        self._audit_log.append(rec)
        if len(self._audit_log) > 500:
            self._audit_log = self._audit_log[-500:]
        logger.info(f"[PERMISSION] Session='{session_id}' Tool='{tool_name}' Risk={risk_level.value} Status={status.value} Reason={reason!r}")

    def get_recent_audit_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent audit records for UI / API telemetry."""
        return [
            {
                "timestamp": r.timestamp,
                "session_id": r.session_id,
                "tool_name": r.tool_name,
                "risk_level": r.risk_level.value,
                "status": r.status.value,
                "reason": r.reason,
            }
            for r in reversed(self._audit_log[-limit:])
        ]


# Singleton instance
permission_manager = PermissionManager()
