"""
test_spotify_free.py — Test suite for Spotify Free Discovery, Ranking & Launcher architecture.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

from app.services.spotify_service import spotify_service
from app.assistant.fast_router import fast_router
from app.assistant.commands import CommandAction


def test_spotify_capabilities():
    caps = spotify_service.get_capabilities()
    assert caps["search"] is True
    assert caps["openSpotify"] is True
    assert caps["directPlayback"] is False


def test_fast_router_music_search():
    # "Find Believer"
    res1 = fast_router.route("Find Believer")
    assert res1.matched is True
    assert res1.action == CommandAction.MUSIC_SEARCH
    assert "Believer" in res1.query

    # "Search Pattuma"
    res2 = fast_router.route("Search Pattuma")
    assert res2.matched is True
    assert res2.action == CommandAction.MUSIC_SEARCH
    assert "Pattuma" in res2.query

    # "Play Pattuma"
    res3 = fast_router.route("Play Pattuma")
    assert res3.matched is True
    assert res3.action == CommandAction.MUSIC_PLAY
    assert "Pattuma" in res3.query


def test_fast_router_artist_search():
    res = fast_router.route("Find songs by A R Rahman")
    assert res.matched is True
    assert res.action == CommandAction.ARTIST_SEARCH
    assert "A R Rahman" in res.parameters["artist"]


def test_fast_router_open_spotify():
    res = fast_router.route("Open Pattuma in Spotify")
    assert res.matched is True
    assert res.action == CommandAction.OPEN_SPOTIFY
    assert "Pattuma" in res.query


def test_free_mode_playback_safe_responses():
    # Calling pause in free mode should not raise an exception
    pause_res = spotify_service.pause()
    assert pause_res["success"] is False
    assert pause_res["requires_premium"] is True

    resume_res = spotify_service.resume()
    assert resume_res["success"] is False
    assert resume_res["requires_premium"] is True


@pytest.mark.asyncio
async def test_api_spotify_capabilities_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/spotify/capabilities")
    assert res.status_code == 200
    data = res.json()
    assert data["search"] is True
    assert data["openSpotify"] is True
    assert data["directPlayback"] is False


@pytest.mark.asyncio
async def test_api_spotify_status_with_capabilities():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/spotify/status")
    assert res.status_code == 200
    data = res.json()
    assert "capabilities" in data
    assert data["capabilities"]["directPlayback"] is False


@pytest.mark.asyncio
async def test_chat_music_search_discovery():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/chat", json={"message": "Search Pattuma", "session_id": "test-free-session"})
    assert res.status_code == 200
    data = res.json()
    # Response must NOT claim "Now playing"
    assert "Now playing" not in data["message"]
    assert "Open it in Spotify" in data["message"] or "Found" in data["message"] or "found" in data["message"]
    # Track payload should be attached if result was found
    if data.get("track"):
        assert "pattuma" in data["track"]["title"].lower()
