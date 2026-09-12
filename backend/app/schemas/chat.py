from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator



class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="The user's message text")
    session_id: Optional[str] = Field(default=None, description="Optional session tracking ID")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Message cannot be blank or whitespace only")
        return cleaned


class SuggestionItem(BaseModel):
    label: str
    action_type: str
    payload: Optional[str] = None


class TrackPayload(BaseModel):
    id: Optional[str] = None
    title: str
    artist: str
    album: Optional[str] = None
    album_art: Optional[str] = None
    audio_url: Optional[str] = None
    duration: Optional[int] = 0
    duration_ms: Optional[int] = 0
    release_date: Optional[str] = None
    release_year: Optional[str] = None
    external_url: Optional[str] = None
    uri: Optional[str] = None
    webpage_url: Optional[str] = None
    ranking_score: Optional[float] = None
    # Provider-aware player fields
    provider: Optional[str] = "youtube"
    video_id: Optional[str] = None
    videoId: Optional[str] = None
    channel_title: Optional[str] = None
    channelTitle: Optional[str] = None
    thumbnail: Optional[str] = None
    # SoundCloud fields
    urn: Optional[str] = None
    creator: Optional[str] = None
    artworkUrl: Optional[str] = None
    permalinkUrl: Optional[str] = None
    access: Optional[str] = None  # "playable", "preview", "blocked"
    streamable: Optional[bool] = True


class ChatResponse(BaseModel):
    message: str
    status: str = "success"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: Optional[str] = None
    suggestions: Optional[List[SuggestionItem]] = None
    track: Optional[TrackPayload] = None
    action: Optional[str] = None
    action_value: Optional[Any] = None
    # Phase 4 AI Brain Telemetry
    intent: Optional[str] = None
    confidence: Optional[float] = None
    tool: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    execution_status: Optional[str] = None




class HealthResponse(BaseModel):
    status: str = "healthy"
    app_name: str
    environment: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
