from fastapi import APIRouter, Query, HTTPException
from app.services.free_music_service import free_music_service
from app.schemas.chat import TrackPayload

router = APIRouter(prefix="/music", tags=["Free Music Streaming"])


@router.get("/search", response_model=TrackPayload)
async def search_free_music(query: str = Query(..., min_length=1, description="Song or artist name")):
    """Search and extract streaming audio URL."""
    result = free_music_service.search_and_extract(query)
    if not result:
        raise HTTPException(status_code=404, detail=f"No audio stream found for query '{query}'")
    return TrackPayload(**result)


@router.get("/youtube/search")
async def search_youtube_music(
    query: str = Query(..., min_length=1, description="Song or artist name"),
    artist: str = Query(None, description="Artist name hint"),
    limit: int = Query(10, ge=1, le=20, description="Max results"),
):
    """Search YouTube Data API v3 with deterministic ranking."""
    from app.services.youtube_service import youtube_service
    res = youtube_service.search_youtube(query=query, artist_hint=artist, limit=limit)
    if not res.get("success"):
        raise HTTPException(
            status_code=400 if res.get("error") == "missing_api_key" else 502,
            detail=res.get("message", "YouTube search failed")
        )
    return res


@router.get("/soundcloud/search")
async def search_soundcloud_music(
    query: str = Query(..., min_length=1, description="Song or artist name"),
    artist: str = Query(None, description="Artist name hint"),
    limit: int = Query(10, ge=1, le=25, description="Max results"),
    access: str = Query("playable", description="Access level: playable, preview, or blocked"),
):
    """Search SoundCloud with deterministic ranking and playable verification."""
    from app.services.soundcloud_service import soundcloud_service
    res = soundcloud_service.search_tracks(
        query=query,
        artist_hint=artist,
        limit=limit,
        access_filter=access,
    )
    if not res.get("success"):
        status_code = 400 if res.get("error") == "missing_credentials" else (429 if res.get("error") == "rate_limited" else 502)
        raise HTTPException(status_code=status_code, detail=res.get("message", "SoundCloud search failed"))
    return res


from typing import Optional


@router.get("/soundcloud/resolve")
async def resolve_soundcloud_playable(
    query: Optional[str] = Query(None, description="Song or artist name"),
    artist: Optional[str] = Query(None, description="Artist name hint"),
    urn: Optional[str] = Query(None, description="SoundCloud track URN (e.g. soundcloud:tracks:12345)"),
):
    """Resolve the best playable SoundCloud track and its streaming audio URL."""
    from app.services.soundcloud_service import soundcloud_service
    if urn:
        stream_url = soundcloud_service.resolve_playable_stream(urn)
        if stream_url:
            return {
                "success": True,
                "urn": urn,
                "audio_url": stream_url,
                "provider": "soundcloud",
            }
        raise HTTPException(status_code=404, detail=f"Playable stream not found for track URN '{urn}'")

    if not query:
        raise HTTPException(status_code=422, detail="Either 'query' or 'urn' must be provided")

    res = soundcloud_service.search_and_resolve_playable(query=query, artist_hint=artist)
    if not res.get("success"):
        raise HTTPException(status_code=404 if res.get("error") == "no_results" else 400, detail=res.get("message", "Playable SoundCloud track not found"))
    return res
