"""
Tests for SoundCloud Audio Playback Provider, Fast Router, and Chat Orchestration.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.soundcloud_service import soundcloud_service
from app.services.soundcloud_ranker import soundcloud_ranker
from app.assistant.fast_router import fast_router
from app.assistant.commands import CommandAction


def test_soundcloud_ranking_and_fallback():
    """Verify ranking and fallback metadata returned by soundcloud_service."""
    res = soundcloud_service.search_tracks("Pattuma", artist_hint="Sai Abhyankkar")
    assert res["success"] is True
    assert res["total"] >= 1
    best = res["best_match"]
    assert best is not None
    assert best["provider"] == "soundcloud"
    assert "Pattuma" in best["title"]
    assert "Sai Abhyankkar" in best["creator"]
    assert best["access"] == "playable"
    assert best["streamable"] is True
    assert best["audio_url"] is not None
    assert best["ranking_score"] > 0


def test_soundcloud_ranker_penalties():
    """Verify ranker scores official/clean tracks higher than covers and remixes."""
    items = [
        {
            "id": 101,
            "urn": "soundcloud:tracks:101",
            "title": "Pattuma - Acoustic Cover",
            "user": {"username": "CoverSinger"},
            "access": "playable",
            "streamable": True,
        },
        {
            "id": 102,
            "urn": "soundcloud:tracks:102",
            "title": "Sai Abhyankkar - Pattuma (Official Audio)",
            "user": {"username": "Sai Abhyankkar"},
            "access": "playable",
            "streamable": True,
        },
        {
            "id": 103,
            "urn": "soundcloud:tracks:103",
            "title": "Pattuma (Club Remix 2024)",
            "user": {"username": "DJRemix"},
            "access": "playable",
            "streamable": True,
        },
    ]
    ranked = soundcloud_ranker.rank_tracks(items, "Pattuma", "Sai Abhyankkar")
    assert len(ranked) == 3
    # Official audio must be highest ranked
    assert ranked[0]["id"] == 102
    assert ranked[0]["ranking_score"] > ranked[1]["ranking_score"]
    assert ranked[0]["ranking_score"] > ranked[2]["ranking_score"]


def test_fast_router_soundcloud_routing():
    """Verify fast router routes generic 'play' commands to SoundCloud provider."""
    # Generic "play <song>" defaults to soundcloud audio playback
    cmd1 = fast_router.route("play Pattuma")
    assert cmd1 is not None
    assert cmd1.action in (CommandAction.MUSIC_PLAY, CommandAction.SOUNDCLOUD_PLAY)
    assert cmd1.parameters.get("provider") == "soundcloud"
    assert "pattuma" in cmd1.parameters.get("query", "").lower()

    # Explicit SoundCloud play
    cmd2 = fast_router.route("play Believer on soundcloud")
    assert cmd2 is not None
    assert cmd2.action in (CommandAction.MUSIC_PLAY, CommandAction.SOUNDCLOUD_PLAY)
    assert cmd2.parameters.get("provider") == "soundcloud"

    # Explicit SoundCloud search
    cmd3 = fast_router.route("search soundcloud for Anirudh")
    assert cmd3 is not None
    assert cmd3.action == CommandAction.SOUNDCLOUD_SEARCH

    # Spotify routing preserved
    cmd4 = fast_router.route("play Starboy on spotify")
    assert cmd4 is not None
    assert cmd4.action in (CommandAction.MUSIC_PLAY, CommandAction.OPEN_SPOTIFY)
    assert cmd4.parameters.get("provider") == "spotify"

    cmd5 = fast_router.route("search spotify for Taylor Swift")
    assert cmd5 is not None
    assert cmd5.action == CommandAction.MUSIC_SEARCH


@pytest.mark.asyncio
async def test_api_soundcloud_search_endpoint():
    """Verify GET /api/music/soundcloud/search returns valid payload."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/music/soundcloud/search?query=Pattuma")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["tracks"]) >= 1
        assert data["best_match"]["provider"] == "soundcloud"
        assert "Pattuma" in data["best_match"]["title"]


@pytest.mark.asyncio
async def test_api_soundcloud_resolve_endpoint():
    """Verify GET /api/music/soundcloud/resolve returns audio stream url."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/music/soundcloud/resolve?urn=soundcloud:tracks:1892019482")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["audio_url"] is not None
        assert "http" in data["audio_url"]


@pytest.mark.asyncio
async def test_chat_soundcloud_playback_flow():
    """Verify chat message triggers SoundCloud playback track in response payload."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/chat", json={"message": "play Pattuma"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] in ("play", "soundcloud_play")
        assert data["track"] is not None
        assert data["track"]["provider"] == "soundcloud"
        assert "Pattuma" in data["track"]["title"]
        assert data["track"]["audio_url"] is not None
        assert "Pattuma" in data["message"]
