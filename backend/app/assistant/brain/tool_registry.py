"""
tool_registry.py — Centralized Tool Registry for Zana AI Brain (Phase 6A).

Defines the complete registry of callable tools with declarative metadata:
  - name: unique tool key
  - version: semantic version string
  - description: LLM and developer readable description
  - permission_id: permission identifier string
  - risk_level: LOW, MEDIUM, or HIGH
  - requires_confirmation: whether user confirmation modal is triggered
  - required_args / optional_args
  - input_schema / output_schema
  - timeout_seconds
  - enabled state
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.assistant.brain.permission_manager import RiskLevel


@dataclass
class ToolDefinition:
    """Enhanced metadata for a single tool in Phase 6A."""

    name: str
    description: str
    version: str = "1.0.0"
    permission_id: str = "tool.execute"
    risk_level: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    required_args: List[str] = field(default_factory=list)
    optional_args: List[str] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 10.0
    enabled: bool = True

    def validate_arguments(self, args: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate that all required arguments are present."""
        missing = [k for k in self.required_args if k not in args]
        if missing:
            return False, f"Tool '{self.name}' missing required args: {missing}"
        return True, None


# ---------------------------------------------------------------------------
# Central Tool Registry — Phase 6A Complete Declarations
# ---------------------------------------------------------------------------

TOOL_REGISTRY: Dict[str, ToolDefinition] = {
    # Music playback tools (LOW risk)
    "music_search_play": ToolDefinition(
        name="music_search_play",
        description="Search for a song/artist/genre and start streaming audio playback.",
        permission_id="music.play",
        risk_level=RiskLevel.LOW,
        required_args=["query"],
        input_schema={"query": "string"},
        output_schema={"track": "TrackPayload", "status": "string"},
    ),
    "music_pause": ToolDefinition(
        name="music_pause",
        description="Pause the currently playing audio.",
        permission_id="music.pause",
        risk_level=RiskLevel.LOW,
    ),
    "music_resume": ToolDefinition(
        name="music_resume",
        description="Resume paused audio playback.",
        permission_id="music.resume",
        risk_level=RiskLevel.LOW,
    ),
    "music_next": ToolDefinition(
        name="music_next",
        description="Skip to the next track. Context-aware.",
        permission_id="music.next",
        risk_level=RiskLevel.LOW,
        optional_args=["context_query"],
    ),
    "music_previous": ToolDefinition(
        name="music_previous",
        description="Go back to restart the current track.",
        permission_id="music.previous",
        risk_level=RiskLevel.LOW,
    ),
    "music_volume": ToolDefinition(
        name="music_volume",
        description="Set the playback volume percentage (0-100).",
        permission_id="music.volume",
        risk_level=RiskLevel.LOW,
        required_args=["volume"],
        input_schema={"volume": "integer"},
    ),
    "music_current_track": ToolDefinition(
        name="music_current_track",
        description="Get information about what is currently playing.",
        permission_id="music.info",
        risk_level=RiskLevel.LOW,
    ),

    # Conversation & Capabilities (LOW risk)
    "chat_response": ToolDefinition(
        name="chat_response",
        description="Generate a natural language conversational response via LLM.",
        permission_id="chat.generate",
        risk_level=RiskLevel.LOW,
        optional_args=["intent", "response_hint", "user_message"],
    ),
    "assistant_capabilities": ToolDefinition(
        name="assistant_capabilities",
        description="Return a description of what Zana can do.",
        permission_id="assistant.info",
        risk_level=RiskLevel.LOW,
    ),
    "assistant_status": ToolDefinition(
        name="assistant_status",
        description="Return current system and connectivity status.",
        permission_id="assistant.status",
        risk_level=RiskLevel.LOW,
    ),

    # Reminders tools (MEDIUM risk)
    "reminder_create": ToolDefinition(
        name="reminder_create",
        description="Schedule a proactive reminder for a specific time.",
        permission_id="reminder.create",
        risk_level=RiskLevel.MEDIUM,
        requires_confirmation=False,
        required_args=["message"],
        optional_args=["scheduled_time", "delay_seconds"],
        input_schema={"message": "string", "scheduled_time": "string"},
    ),
    "reminder_list": ToolDefinition(
        name="reminder_list",
        description="List all scheduled reminders for the user.",
        permission_id="reminder.list",
        risk_level=RiskLevel.LOW,
    ),
    "reminder_delete": ToolDefinition(
        name="reminder_delete",
        description="Cancel or delete a scheduled reminder.",
        permission_id="reminder.delete",
        risk_level=RiskLevel.MEDIUM,
        requires_confirmation=True,
        required_args=["reminder_id"],
        input_schema={"reminder_id": "string"},
    ),

    # Memory & Profile management (HIGH risk for clear/delete)
    "memory_clear_all": ToolDefinition(
        name="memory_clear_all",
        description="Clear all long-term user memories for the session.",
        permission_id="memory.clear",
        risk_level=RiskLevel.HIGH,
        requires_confirmation=True,
    ),
}


def get_tool(name: str) -> Optional[ToolDefinition]:
    """Return a ToolDefinition by name, or None if not found."""
    return TOOL_REGISTRY.get(name)


def is_valid_tool(name: str) -> bool:
    """Return True if the tool name is registered and enabled."""
    tool = TOOL_REGISTRY.get(name)
    return tool is not None and tool.enabled


def get_tool_descriptions_for_prompt() -> str:
    """Return a compact description of all enabled tools for LLM system prompts."""
    lines = []
    for tool in TOOL_REGISTRY.values():
        if not tool.enabled:
            continue
        args = ", ".join(tool.required_args) if tool.required_args else "none"
        lines.append(f"- {tool.name}: {tool.description} (required args: {args}, risk: {tool.risk_level.value})")
    return "\n".join(lines)
