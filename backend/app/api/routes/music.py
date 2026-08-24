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
