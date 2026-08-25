"""
tool_executor.py — Executes registered tools for Zana AI Brain.

Bridges the AI Brain to the existing service layer:
  - free_music_service  (yt-dlp streaming)
  - spotify_service     (Spotify API)
  - context_manager     (for current track lookups)

Returns structured ToolResult objects.
Never allows arbitrary code execution.
All tool names must be registered in tool_registry.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.core.logging_config import logger
from app.services.spotify_service import spotify_service
from app.services.free_music_service import free_music_service
from app.assistant.brain.tool_registry import TOOL_REGISTRY, is_valid_tool
from app.assistant.brain.context_manager import ConversationContext


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ToolResult:
    """Structured result from a single tool execution."""

    success: bool
    tool: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    # Convenience fields populated by music tools
    track_title: Optional[str] = None
    track_artist: Optional[str] = None
    track_payload: Optional[Dict[str, Any]] = None  # Full TrackPayload-compatible dict
    action: Optional[str] = None                    # pause / resume / volume / seek
    action_value: Optional[Any] = None

    def __repr__(self) -> str:
        return (
            f"ToolResult(success={self.success}, tool={self.tool!r}, "
            f"error={self.error!r})"
        )


# ---------------------------------------------------------------------------
# Tool Executor
# ---------------------------------------------------------------------------

class ToolExecutor:
    """
    Executes a single tool by name with the given arguments.

    All execution is delegated to the existing service layer.
    This class does NOT create new services.
    """

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        ctx: Optional[ConversationContext] = None,
    ) -> ToolResult:
        """
        Execute the named tool and return a ToolResult.

        Parameters
        ----------
        tool_name:  Must be a key in TOOL_REGISTRY.
        arguments:  Dict of tool arguments.
        ctx:        Current conversation context (for context-aware tools).
        """
        # ── Guard: tool must be registered ──────────────────────────────────
        if not is_valid_tool(tool_name):
            logger.warning(f"[AI-BRAIN] Unknown tool requested: {tool_name!r}")
            return ToolResult(
                success=False,
                tool=tool_name,
                error=f"Tool '{tool_name}' is not available.",
            )

        # ── Validate arguments ───────────────────────────────────────────────
        tool_def = TOOL_REGISTRY[tool_name]
        valid, err_msg = tool_def.validate_arguments(arguments)
        if not valid:
            logger.warning(f"[AI-BRAIN] Invalid arguments for {tool_name!r}: {err_msg}")
            return ToolResult(success=False, tool=tool_name, error=err_msg)

        logger.info(f"[AI-BRAIN] Tool: {tool_name} | Args: {arguments}")

        # ── Route to handler ─────────────────────────────────────────────────
        try:
            if tool_name == "music_search_play":
                return await self._music_search_play(arguments, ctx)
            elif tool_name == "music_pause":
                return self._music_pause()
            elif tool_name == "music_resume":
                return self._music_resume()
            elif tool_name == "music_next":
                return await self._music_next(arguments, ctx)
            elif tool_name == "music_previous":
                return self._music_previous()
            elif tool_name == "music_volume":
                return self._music_volume(arguments)
            elif tool_name == "music_current_track":
                return self._music_current_track(ctx)
            elif tool_name in ("chat_response", "assistant_capabilities", "assistant_status"):
                # These are handled by the response_generator, not here
                return ToolResult(
                    success=True,
                    tool=tool_name,
                    data={"handled_by": "response_generator"},
                )
            else:
                return ToolResult(
                    success=False,
                    tool=tool_name,
                    error=f"No handler implemented for tool: {tool_name}",
                )
        except Exception as exc:
            logger.error(
                f"[AI-BRAIN] Unhandled exception in tool {tool_name!r}: {exc}",
                exc_info=True,
            )
            return ToolResult(
                success=False,
                tool=tool_name,
                error=f"An unexpected error occurred: {str(exc)}",
            )

    # ── Tool handlers ────────────────────────────────────────────────────────

    async def _music_search_play(
        self, args: Dict[str, Any], ctx: Optional[ConversationContext]
    ) -> ToolResult:
        query = str(args.get("query", "")).strip()
        logger.info(f"[AI-BRAIN] music_search_play: query={query!r}")

        try:
            track_info = free_music_service.search_and_extract(query)
        except Exception as exc:
            logger.error(f"[AI-BRAIN] free_music_service error: {exc}")
            track_info = None

        if track_info and track_info.get("audio_url"):
            payload = {
                "id": track_info.get("id"),
                "title": track_info.get("title", query),
                "artist": track_info.get("artist", "Unknown Artist"),
                "album_art": track_info.get("album_art"),
                "audio_url": track_info.get("audio_url"),
                "duration": track_info.get("duration", 0),
                "webpage_url": track_info.get("webpage_url"),
            }
            return ToolResult(
                success=True,
                tool="music_search_play",
                data={"query": query},
                track_title=payload["title"],
                track_artist=payload["artist"],
                track_payload=payload,
                action="play",
            )

        # Fallback: try Spotify
        if spotify_service.is_authenticated():
            sp_result = spotify_service.search_and_play(query)
            if sp_result.get("success"):
                track = sp_result.get("track", {})
                return ToolResult(
                    success=True,
                    tool="music_search_play",
                    data={"query": query, "via": "spotify"},
                    track_title=track.get("name", query),
                    track_artist=track.get("artists", ""),
                )

        return ToolResult(
            success=False,
            tool="music_search_play",
            error=f"Could not find a stream for \"{query}\". Try a different song title.",
        )

    def _music_pause(self) -> ToolResult:
        logger.info("[AI-BRAIN] music_pause")
        return ToolResult(
            success=True,
            tool="music_pause",
            action="pause",
        )

    def _music_resume(self) -> ToolResult:
        logger.info("[AI-BRAIN] music_resume")
        return ToolResult(
            success=True,
            tool="music_resume",
            action="resume",
        )

    async def _music_next(
        self, args: Dict[str, Any], ctx: Optional[ConversationContext]
    ) -> ToolResult:
        """
        Context-aware next track.
        Uses last played artist/query from context instead of the old hardcoded "Starboy".
        """
        # Build a smart next-track query from context
        next_query = args.get("context_query", "")

        if not next_query and ctx and ctx.has_music_context():
            if ctx.last_played_artist and ctx.last_played_artist != "Unknown Artist":
                next_query = ctx.last_played_artist
            elif ctx.last_played_query:
                next_query = ctx.last_played_query

        if not next_query:
            next_query = "popular hits"  # Sensible default

        logger.info(f"[AI-BRAIN] music_next: searching for next track like {next_query!r}")

        try:
            track_info = free_music_service.search_and_extract(next_query)
        except Exception as exc:
            logger.error(f"[AI-BRAIN] music_next search error: {exc}")
            track_info = None

        if track_info and track_info.get("audio_url"):
            payload = {
                "id": track_info.get("id"),
                "title": track_info.get("title", next_query),
                "artist": track_info.get("artist", "Unknown Artist"),
                "album_art": track_info.get("album_art"),
                "audio_url": track_info.get("audio_url"),
                "duration": track_info.get("duration", 0),
                "webpage_url": track_info.get("webpage_url"),
            }
            return ToolResult(
                success=True,
                tool="music_next",
                data={"query": next_query},
                track_title=payload["title"],
                track_artist=payload["artist"],
                track_payload=payload,
                action="play",
            )

        return ToolResult(
            success=False,
            tool="music_next",
            error="Couldn't find a next track to play.",
        )

    def _music_previous(self) -> ToolResult:
        logger.info("[AI-BRAIN] music_previous")
        return ToolResult(
            success=True,
            tool="music_previous",
            action="seek",
            action_value=0,
        )

    def _music_volume(self, args: Dict[str, Any]) -> ToolResult:
        try:
            vol = int(args.get("volume", 75))
            clamped = max(0, min(100, vol))
        except (TypeError, ValueError):
            return ToolResult(
                success=False,
                tool="music_volume",
                error="Invalid volume value. Please specify a number between 0 and 100.",
            )
        logger.info(f"[AI-BRAIN] music_volume: {clamped}%")
        return ToolResult(
            success=True,
            tool="music_volume",
            data={"volume": clamped},
            action="volume",
            action_value=clamped / 100.0,
        )

    def _music_current_track(
        self, ctx: Optional[ConversationContext]
    ) -> ToolResult:
        """
        Return information about the currently playing track.
        Checks Spotify first, then falls back to conversation context.
        """
        logger.info("[AI-BRAIN] music_current_track")

        # Try Spotify
        if spotify_service.is_authenticated():
            try:
                state = spotify_service.get_playback_state()
                track = state.get("track")
                if track and state.get("is_playing"):
                    return ToolResult(
                        success=True,
                        tool="music_current_track",
                        data={
                            "source": "spotify",
                            "track_name": track.get("name"),
                            "artists": track.get("artists"),
                            "album": track.get("album"),
                            "is_playing": True,
                        },
                        track_title=track.get("name"),
                        track_artist=track.get("artists"),
                    )
            except Exception as exc:
                logger.warning(f"[AI-BRAIN] Spotify current track error: {exc}")

        # Fall back to conversation context
        if ctx and ctx.has_music_context():
            return ToolResult(
                success=True,
                tool="music_current_track",
                data={
                    "source": "context",
                    "track_name": ctx.last_played_track,
                    "artists": ctx.last_played_artist,
                    "query": ctx.last_played_query,
                },
                track_title=ctx.last_played_track,
                track_artist=ctx.last_played_artist,
            )

        return ToolResult(
            success=False,
            tool="music_current_track",
            error="Nothing is currently playing.",
        )


# Singleton instance
tool_executor = ToolExecutor()
