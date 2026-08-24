from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel


class CommandAction(str, Enum):
    GREETING = "greeting"
    HELP = "help"
    STATUS = "status"
    UNKNOWN = "unknown"
    # Future Phase 2+ actions:
    MUSIC_SEARCH_PLAY = "music_search_play"
    MUSIC_PAUSE = "music_pause"
    MUSIC_RESUME = "music_resume"
    MUSIC_NEXT = "music_next"
    MUSIC_PREVIOUS = "music_previous"
    MUSIC_VOLUME = "music_volume"


class ParsedCommand(BaseModel):
    action: CommandAction
    query: Optional[str] = None
    parameters: Dict[str, Any] = {}
    confidence: float = 1.0
