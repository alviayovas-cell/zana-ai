import io
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/")
    assert res.status_code == 200
    data = res.json()
    assert "running" in data["message"]


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "Zana AI Assistant"


@pytest.mark.asyncio
async def test_chat_greeting():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/chat", json={"message": "hello"})
    assert res.status_code == 200
    data = res.json()
    assert "Zana" in data["message"]
    assert len(data["suggestions"]) > 0


@pytest.mark.asyncio
async def test_chat_help():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/chat", json={"message": "help"})
    assert res.status_code == 200
    data = res.json()
    assert "Music Playback" in data["message"]


@pytest.mark.asyncio
async def test_chat_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/chat", json={"message": "status"})
    assert res.status_code == 200
    data = res.json()
    assert "System Status" in data["message"]


@pytest.mark.asyncio
async def test_chat_music_play_unauthenticated():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/chat", json={"message": "play Shape of You"})
    assert res.status_code == 200
    data = res.json()
    assert "shape of you" in data["message"].lower()
    assert data["track"] is not None
    assert "title" in data["track"]


@pytest.mark.asyncio
async def test_voice_transcribe_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        files = {"file": ("test.webm", b"fake-audio-bytes", "audio/webm")}
        res = await ac.post("/api/voice/transcribe", files=files)
    assert res.status_code == 200
    data = res.json()
    assert "transcript" in data


@pytest.mark.asyncio
async def test_spotify_auth_url():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/spotify/auth-url")
    assert res.status_code == 200
    data = res.json()
    assert "url" in data
    assert "accounts.spotify.com" in data["url"]


@pytest.mark.asyncio
async def test_spotify_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/spotify/status")
    assert res.status_code == 200
    data = res.json()
    assert "is_authenticated" in data


@pytest.mark.asyncio
async def test_spotify_player_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/spotify/player")
    assert res.status_code == 200
    data = res.json()
    assert "is_connected" in data
