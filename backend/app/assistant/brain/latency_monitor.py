"""
latency_monitor.py — Request Tracing & Latency Monitoring for Zana (Phase 6A).

Tracks per-request latency breakdowns and calculates aggregated metrics:
  - request_id, user_id, session_id
  - intent, tool
  - stt_ms, router_ms, memory_ms, llm_ms, tool_ms, tts_ms, total_ms
  - success, error_type

Provides P50, P95, average latency, and subsystem failure rate metrics.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.logging_config import logger


@dataclass
class LatencyTraceRecord:
    request_id: str
    session_id: str
    intent: str = "UNKNOWN"
    tool: Optional[str] = None
    stt_ms: float = 0.0
    router_ms: float = 0.0
    memory_ms: float = 0.0
    llm_ms: float = 0.0
    tool_ms: float = 0.0
    tts_ms: float = 0.0
    total_ms: float = 0.0
    success: bool = True
    error_type: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class LatencyMonitor:
    """
    In-memory tracer and metric aggregator for developer telemetry.
    Stores last 1000 request traces.
    """

    def __init__(self) -> None:
        self._traces: List[LatencyTraceRecord] = []

    def record_trace(self, trace: LatencyTraceRecord) -> None:
        """Record a completed request trace."""
        self._traces.append(trace)
        if len(self._traces) > 1000:
            self._traces = self._traces[-1000:]
        logger.info(
            f"[LATENCY] Req={trace.request_id[:8]} Total={trace.total_ms:.1f}ms "
            f"(Router={trace.router_ms:.1f}ms, LLM={trace.llm_ms:.1f}ms, Tool={trace.tool_ms:.1f}ms) "
            f"Success={trace.success}"
        )

    def get_metrics(self) -> Dict[str, Any]:
        """
        Calculate aggregated metrics: avg, P50, P95, success rate, failure rates.
        """
        if not self._traces:
            return {
                "total_requests": 0,
                "average_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "success_rate_pct": 100.0,
                "llm_failure_rate_pct": 0.0,
                "tool_failure_rate_pct": 0.0,
                "stt_failure_rate_pct": 0.0,
                "tts_failure_rate_pct": 0.0,
            }

        totals = sorted(t.total_ms for t in self._traces)
        n = len(totals)
        avg = sum(totals) / n
        p50 = totals[math.floor(n * 0.50)]
        p95 = totals[min(math.floor(n * 0.95), n - 1)]

        successful = sum(1 for t in self._traces if t.success)
        success_rate = (successful / n) * 100.0

        llm_fails = sum(1 for t in self._traces if t.error_type == "LLM_ERROR")
        tool_fails = sum(1 for t in self._traces if t.error_type == "TOOL_ERROR")
        stt_fails = sum(1 for t in self._traces if t.error_type == "STT_ERROR")
        tts_fails = sum(1 for t in self._traces if t.error_type == "TTS_ERROR")

        return {
            "total_requests": n,
            "average_latency_ms": round(avg, 2),
            "p50_latency_ms": round(p50, 2),
            "p95_latency_ms": round(p95, 2),
            "success_rate_pct": round(success_rate, 2),
            "llm_failure_rate_pct": round((llm_fails / n) * 100.0, 2),
            "tool_failure_rate_pct": round((tool_fails / n) * 100.0, 2),
            "stt_failure_rate_pct": round((stt_fails / n) * 100.0, 2),
            "tts_failure_rate_pct": round((tts_fails / n) * 100.0, 2),
        }

    def get_recent_traces(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return raw trace dicts for developer dashboard."""
        return [
            {
                "request_id": t.request_id,
                "session_id": t.session_id,
                "intent": t.intent,
                "tool": t.tool,
                "router_ms": round(t.router_ms, 1),
                "llm_ms": round(t.llm_ms, 1),
                "tool_ms": round(t.tool_ms, 1),
                "total_ms": round(t.total_ms, 1),
                "success": t.success,
                "timestamp": t.timestamp,
            }
            for t in reversed(self._traces[-limit:])
        ]


# Singleton instance
latency_monitor = LatencyMonitor()
