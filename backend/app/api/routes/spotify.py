from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.services.spotify_service import spotify_service
from app.core.config import settings
from app.core.logging_config import logger

router = APIRouter(prefix="/spotify", tags=["Spotify"])


class PlayerControlRequest(BaseModel):
    action: str  # play, pause, resume, next, previous, volume
    query: Optional[str] = None
    item_type: Optional[str] = "track"
    volume_percent: Optional[int] = None


@router.get("/capabilities")
async def get_capabilities():
    """Returns the Spotify feature capabilities for the current configuration."""
    return spotify_service.get_capabilities()


@router.get("/search")
async def search_spotify(
    query: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=10, description="Max 10 results for Development Mode"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    artist: Optional[str] = Query(None, description="Optional artist hint"),
    language: Optional[str] = Query(None, description="Optional language hint (e.g. Tamil)"),
):
    """
    Search Spotify catalog with pagination (limit <= 10) and deterministic ranking.
    """
    res = spotify_service.search_spotify(
        query=query,
        item_type="track",
        limit=limit,
        offset=offset,
        artist_hint=artist,
        language_hint=language,
    )
    if not res.get("success"):
        raise HTTPException(status_code=400 if res.get("error") != "spotify_rate_limited" else 429, detail=res.get("message", "Search failed"))
    return res


@router.get("/auth-url")
async def get_auth_url():
    """Returns Spotify login URL."""
    try:
        url = spotify_service.get_authorize_url()
        is_auth = spotify_service.is_authenticated()
        return {"url": url, "is_authenticated": is_auth}
    except Exception as e:
        logger.error(f"Error generating Spotify auth URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
async def spotify_callback(code: Optional[str] = Query(None), error: Optional[str] = Query(None)):
    """Handles Spotify OAuth callback and redirects to frontend."""
    if error:
        logger.error(f"Spotify callback returned error: {error}")
        return RedirectResponse(f"{settings.SPOTIFY_FRONTEND_REDIRECT}?spotify=error&reason={error}")

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    try:
        spotify_service.handle_callback(code)
        logger.info("Spotify authentication successful!")
        return RedirectResponse(f"{settings.SPOTIFY_FRONTEND_REDIRECT}?spotify=connected")
    except Exception as e:
        logger.error(f"Error during Spotify callback exchange: {e}")
        return RedirectResponse(f"{settings.SPOTIFY_FRONTEND_REDIRECT}?spotify=error&reason=exchange_failed")


@router.get("/status")
async def get_spotify_status():
    """Check Spotify login status, user profile, and capability matrix."""
    is_auth = spotify_service.is_authenticated()
    user = spotify_service.get_current_user() if is_auth else None
    return {
        "is_authenticated": is_auth,
        "user": user,
        "capabilities": spotify_service.get_capabilities(),
    }


@router.get("/player")
async def get_player_state():
    """Get current Spotify playback state."""
    return spotify_service.get_playback_state()


@router.post("/player/control")
async def control_player(request: PlayerControlRequest):
    """Execute playback actions safely in Free mode."""
    action = request.action.lower()

    if action == "play":
        if not request.query:
            return spotify_service.resume()
        return spotify_service.search_and_play(request.query, request.item_type or "track")
    elif action == "pause":
        return spotify_service.pause()
    elif action == "resume":
        return spotify_service.resume()
    elif action == "next":
        return spotify_service.next_track()
    elif action == "previous":
        return spotify_service.previous_track()
    elif action == "volume":
        if request.volume_percent is None:
            raise HTTPException(status_code=400, detail="volume_percent required")
        return spotify_service.set_volume(request.volume_percent)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
