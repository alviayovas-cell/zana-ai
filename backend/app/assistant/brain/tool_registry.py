"""
tool_registry.py — Tool definitions for Zana AI Brain.

Defines the complete registry of callable tools.
Each tool has:
  - name: unique identifier
  - description: human/LLM-readable description
  - required_args: argument names that must be present
  - optional_args: argument names that may be present

No arbitrary code execution. Only pre-defined tools registered here.
Execution logic lives in tool_executor.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ToolDefinition:
    """Metadata for a single tool."""

    name: str
    description: str
    required_args: List[str] = field(default_factory=list)
    optional_args: List[str] = field(default_factory=list)

    def validate_arguments(self, args: Dict) -> tuple[bool, Optional[str]]:
        """
        Validate that all required arguments are present.

        Returns
        -------
        (is_valid: bool, error_message: str | None)
        """
        missing = [k for k in self.required_args if k not in args]
        if missing:
            return False, f"Tool '{self.name}' missing required args: {missing}"
        return True, None

    def __repr__(self) -> str:
        return f"ToolDefinition(name={self.name!r})"


# ---------------------------------------------------------------------------
# Tool registry — all available tools
# ---------------------------------------------------------------------------

TOOL_REGISTRY: Dict[str, ToolDefinition] = {
    # Music tools
    "music_search_play": ToolDefinition(
        name="music_search_play",
        description="Search for a song/artist/genre and start streaming audio playback.",
        required_args=["query"],
        optional_args=[],
    ),
    "music_pause": ToolDefinition(
        name="music_pause",
        description="Pause the currently playing audio.",
        required_args=[],
        optional_args=[],
    ),
    "music_resume": ToolDefinition(
        name="music_resume",
        description="Resume paused audio playback.",
        required_args=[],
        optional_args=[],
    ),
    "music_next": ToolDefinition(
        name="music_next",
        description="Skip to the next track. Context-aware: uses last played artist/genre if available.",
        required_args=[],
        optional_args=["context_query"],
    ),
    "music_previous": ToolDefinition(
        name="music_previous",
        description="Go back to restart the current track from the beginning.",
        required_args=[],
        optional_args=[],
    ),
    "music_volume": ToolDefinition(
        name="music_volume",
        description="Set the playback volume to a specific percentage (0-100).",
        required_args=["volume"],
        optional_args=[],
    ),
    "music_current_track": ToolDefinition(
        name="music_current_track",
        description="Get information about what is currently playing.",
        required_args=[],
        optional_args=[],
    ),

    # Conversation tools
    "chat_response": ToolDefinition(
        name="chat_response",
        description="Generate a natural language conversational response via LLM.",
        required_args=[],
        optional_args=["intent", "response_hint", "user_message"],
    ),

    # Assistant tools
    "assistant_capabilities": ToolDefinition(
        name="assistant_capabilities",
        description="Return a description of what Zana can do.",
        required_args=[],
        optional_args=[],
    ),
    "assistant_status": ToolDefinition(
        name="assistant_status",
        description="Return current system and connectivity status.",
        required_args=[],
        optional_args=[],
    ),
}


def get_tool(name: str) -> Optional[ToolDefinition]:
    """Return a ToolDefinition by name, or None if not found."""
    return TOOL_REGISTRY.get(name)


def is_valid_tool(name: str) -> bool:
    """Return True if the tool name is registered."""
    return name in TOOL_REGISTRY


def get_tool_descriptions_for_prompt() -> str:
    """Return a compact description of all tools for LLM system prompts."""
    lines = []
    for tool in TOOL_REGISTRY.values():
        args = ", ".join(tool.required_args) if tool.required_args else "none"
        lines.append(f"- {tool.name}: {tool.description} (required args: {args})")
    return "\n".join(lines)
