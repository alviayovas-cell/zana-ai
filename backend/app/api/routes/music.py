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
