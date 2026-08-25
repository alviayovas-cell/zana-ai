"""
test_phase6a.py — Phase 6A Automated & Integration Tests.

Validates:
  1. Permission System & Risk Levels (LOW, MEDIUM, HIGH)
  2. Tool Registry metadata & validation
  3. Latency Monitoring & Tracing metrics (/api/metrics)
  4. Personal Profiles REST API (/api/profile)
  5. Proactive Reminders CRUD & Due checking (/api/reminders)
  6. Multilingual language detection & STT/TTS routing
  7. SSE Streaming response endpoint (/api/chat/stream)
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

from app.assistant.brain.permission_manager import permission_manager, RiskLevel, PermissionStatus
from app.assistant.brain.tool_registry import TOOL_REGISTRY, get_tool, is_valid_tool
from app.assistant.brain.latency_monitor import latency_monitor, LatencyTraceRecord
from app.services.multilingual_service import multilingual_service


# 1. Permission System Tests
def test_permission_system_low_risk():
    res = permission_manager.evaluate("music_play", session_id="test-p6a", risk_level=RiskLevel.LOW)
    assert res.status == PermissionStatus.ALLOWED
    assert res.requires_confirmation is False


def test_permission_system_high_risk_requires_confirmation():
    res = permission_manager.evaluate("memory_clear_all", session_id="test-p6a", risk_level=RiskLevel.HIGH, user_confirmed=False)
    assert res.status == PermissionStatus.REQUIRES_CONFIRMATION
    assert res.requires_confirmation is True


def test_permission_system_high_risk_confirmed():
    res = permission_manager.evaluate("memory_clear_all", session_id="test-p6a", risk_level=RiskLevel.HIGH, user_confirmed=True)
    assert res.status == PermissionStatus.ALLOWED


# 2. Tool Registry Tests
def test_tool_registry_enhanced_fields():
    tool = get_tool("music_search_play")
    assert tool is not None
    assert tool.permission_id == "music.play"
    assert tool.risk_level == RiskLevel.LOW
    assert is_valid_tool("music_search_play") is True


def test_tool_registry_reminder_tools():
    assert is_valid_tool("reminder_create") is True
    assert get_tool("reminder_delete").risk_level == RiskLevel.MEDIUM


# 3. Multilingual Routing Tests
def test_multilingual_english():
    assert multilingual_service.detect_language("Play a song") == "en"


def test_multilingual_tamil_script():
    assert multilingual_service.detect_language("பாடல் ஒன்றை இயக்கு") == "ta"


def test_multilingual_hindi_script():
    assert multilingual_service.detect_language("एक गाना बजाओ") == "hi"


# 4. Latency Monitor Unit Tests
def test_latency_monitor_metrics():
    latency_monitor.record_trace(LatencyTraceRecord(request_id="req-1", session_id="s1", total_ms=100.0, router_ms=5.0, llm_ms=80.0))
    latency_monitor.record_trace(LatencyTraceRecord(request_id="req-2", session_id="s1", total_ms=200.0, router_ms=5.0, llm_ms=180.0))
    metrics = latency_monitor.get_metrics()
    assert metrics["total_requests"] >= 2
    assert metrics["average_latency_ms"] > 0
    assert metrics["p50_latency_ms"] > 0


# 5. REST API Integration Tests
@pytest.mark.asyncio
async def test_api_metrics_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "average_latency_ms" in data


@pytest.mark.asyncio
async def test_api_profile_crud():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Get
        res_get = await ac.get("/api/profile?user_id=test-p6a-user")
        assert res_get.status_code == 200
        # Update
        res_post = await ac.post("/api/profile", json={
            "user_id": "test-p6a-user",
            "display_name": "Alvia",
            "preferred_language": "ta",
            "wake_word_enabled": True
        })
        assert res_post.status_code == 200
        data = res_post.json()
        assert data["display_name"] == "Alvia"
        assert data["preferred_language"] == "ta"


@pytest.mark.asyncio
async def test_api_reminders_crud():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create
        res_create = await ac.post("/api/reminders", json={
            "user_id": "test-p6a-user",
            "message": "Test reminder for Phase 6A",
            "delay_seconds": 10
        })
        assert res_create.status_code == 200
        created_data = res_create.json()
        assert created_data["success"] is True
        rem_id = created_data["reminder"]["id"]

        # List
        res_list = await ac.get("/api/reminders?user_id=test-p6a-user")
        assert res_list.status_code == 200
        assert res_list.json()["count"] >= 1

        # Delete
        res_del = await ac.delete(f"/api/reminders/{rem_id}?user_id=test-p6a-user")
        assert res_del.status_code == 200
        assert res_del.json()["success"] is True


@pytest.mark.asyncio
async def test_api_chat_stream_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/chat/stream", json={"message": "hello", "session_id": "stream-test"})
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
