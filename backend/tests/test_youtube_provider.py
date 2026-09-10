"""
Tests for YouTube Music Playback Provider, Fast Command Router, and Orchestrator Integration.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.youtube_service import youtube_service
from app.services.music_ranker import youtube_ranker
from app.assistant.fast_router import fast_router
from app.schemas.commands import CommandAction


def test_youtube_ranking_and_fallback():
    """Verify ranking and fallback metadata returned by YouTubeService."""
    res = youtube_service.search_youtube("Believer", artist_hint="Imagine Dragons")
    assert res["success"] is True
    assert res["total"] >= 1
    best = res["best_match"]
    assert best is not None
    assert best["provider"] == "youtube"
    assert best["videoId"] == "7wtfhZwyrcc"
    assert "Believer" in best["title"]
    assert best["duration"] == 216
    assert best["ranking_score"] > 0


def test_youtube_regional_tamil_fallback():
    """Verify regional song query fallback and ranking."""
    res = youtube_service.search_youtube("Pattuma", artist_hint="Sai Abhyankkar")
    assert res["success"] is True
    best = res["best_match"]
    assert best is not None
    assert best["videoId"] == "qj3rkXWks10"
    assert "Pattuma" in best["title"]


def test_fast_router_youtube_play():
    """Verify fast router accurately captures play commands for YouTube."""
    cmd = fast_router.route("play Believer")
    assert cmd is not None
    assert cmd.action in (CommandAction.MUSIC_PLAY, CommandAction.YOUTUBE_PLAY)
    assert "believer" in cmd.parameters.get("query", "").lower()

    cmd2 = fast_router.route("play Pattuma on youtube")
    assert cmd2 is not None
    assert cmd2.action in (CommandAction.MUSIC_PLAY, CommandAction.YOUTUBE_PLAY)
    assert cmd2.parameters.get("provider") == "youtube"
    assert "pattuma" in cmd2.parameters.get("query", "").lower()

    cmd3 = fast_router.route("listen to Arijit Singh")
    assert cmd3 is not None
    assert cmd3.action in (CommandAction.MUSIC_PLAY, CommandAction.YOUTUBE_PLAY)


def test_music_ranker_scoring():
    """Verify scoring logic favors official music videos and clean titles."""
    items = [
        {
            "id": {"videoId": "cover1"},
            "snippet": {
                "title": "Believer - Guitar Cover by Someone",
                "channelTitle": "RandomGuitarist",
            },
        },
        {
            "id": {"videoId": "official1"},
            "snippet": {
                "title": "Imagine Dragons - Believer (Official Music Video)",
                "channelTitle": "ImagineDragonsVEVO",
            },
        },
    ]
    ranked = youtube_ranker.rank_videos(items, "Believer", "Imagine Dragons")
    assert len(ranked) == 2
    # Official video must be ranked highest
    assert ranked[0]["videoId"] == "official1"
    assert ranked[0]["ranking_score"] > ranked[1]["ranking_score"]


@pytest.mark.asyncio
async def test_api_youtube_search_endpoint():
    """Verify GET /api/music/youtube/search returns valid payload."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/music/youtube/search?query=Believer")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["tracks"]) >= 1
        assert data["best_match"]["provider"] == "youtube"


@pytest.mark.asyncio
async def test_chat_youtube_playback_flow():
    """Verify chat message triggers YouTube playback track in response payload."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/chat", json={"message": "play Believer by Imagine Dragons"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] in ("play", "youtube_play")
        assert data["track"] is not None
        assert data["track"]["provider"] == "youtube"
        assert data["track"]["videoId"] == "7wtfhZwyrcc"
        assert "Believer" in data["message"]
