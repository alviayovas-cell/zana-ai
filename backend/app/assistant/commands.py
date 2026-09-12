from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel


class CommandAction(str, Enum):
    # Phase 1–3 actions (regex fast path — unchanged)
    GREETING = "greeting"
    HELP = "help"
    STATUS = "status"
    UNKNOWN = "unknown"
    MUSIC_SEARCH_PLAY = "music_search_play"
    MUSIC_PLAY = "music_play"
    YOUTUBE_PLAY = "youtube_play"
    SOUNDCLOUD_PLAY = "soundcloud_play"
    SOUNDCLOUD_SEARCH = "soundcloud_search"
    MUSIC_PAUSE = "music_pause"
    MUSIC_RESUME = "music_resume"
    MUSIC_NEXT = "music_next"
    MUSIC_PREVIOUS = "music_previous"
    MUSIC_VOLUME = "music_volume"

    # Phase 4: AI Brain intents
    MUSIC_CURRENT_TRACK = "music_current_track"
    MUSIC_INFORMATION = "music_information"
    GENERAL_CONVERSATION = "general_conversation"
    ASSISTANT_CAPABILITIES = "assistant_capabilities"
    CLARIFICATION_NEEDED = "clarification_needed"

    # Music Discovery & Spotify Launcher intents
    MUSIC_SEARCH = "music_search"
    ARTIST_SEARCH = "artist_search"
    ALBUM_SEARCH = "album_search"
    OPEN_SPOTIFY = "open_spotify"


class ParsedCommand(BaseModel):
    action: CommandAction
    query: Optional[str] = None
    parameters: Dict[str, Any] = {}
    confidence: float = 1.0
