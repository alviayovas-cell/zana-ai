"""
metrics.py — Developer Latency & Observability REST API (Phase 6A).

Endpoints:
  GET /api/metrics         — Aggregated P50, P95, failure rate metrics
  GET /api/metrics/traces  — Recent request traces
"""
from __future__ import annotations

from fastapi import APIRouter
from app.assistant.brain.latency_monitor import latency_monitor

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("")
async def get_metrics():
    """Return aggregated latency & system health metrics."""
    return latency_monitor.get_metrics()


@router.get("/traces")
async def get_traces(limit: int = 20):
    """Return recent request latency trace logs."""
    return {"traces": latency_monitor.get_recent_traces(limit=limit)}
