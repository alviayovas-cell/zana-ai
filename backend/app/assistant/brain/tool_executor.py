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
from app.services.youtube_service import youtube_service
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
            if tool_name == "music_play":
                return await self._music_play(arguments, ctx)
            elif tool_name == "soundcloud_search":
                return await self._soundcloud_search(arguments, ctx)
            elif tool_name == "youtube_search":
                return await self._youtube_search(arguments, ctx)
            elif tool_name in ("music_search", "music_search_play"):
                if arguments.get("provider") == "soundcloud":
                    return await self._music_play(arguments, ctx)
                elif arguments.get("provider") == "youtube":
                    return await self._music_play(arguments, ctx)
                return await self._music_search(arguments, ctx)
            elif tool_name == "artist_search":
                return await self._artist_search(arguments, ctx)
            elif tool_name == "album_search":
                return await self._album_search(arguments, ctx)
            elif tool_name == "playlist_search":
                return await self._playlist_search(arguments, ctx)
            elif tool_name == "open_spotify":
                return await self._open_spotify(arguments, ctx)
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

    async def _music_play(
        self, args: Dict[str, Any], ctx: Optional[ConversationContext]
    ) -> ToolResult:
        """
        Play a song in the Zana player.
        Defaults to SoundCloud provider for in-page audio streaming.
        Supports explicit YouTube and Spotify routing.
        """
        provider = str(args.get("provider", "soundcloud")).lower().strip()
        query = str(args.get("query", args.get("track", ""))).strip()
        artist_hint = args.get("artist")

        if not query and ctx and ctx.current_track:
            query = ctx.current_track.title
            if not artist_hint:
                artist_hint = ctx.current_track.artist

        if not query:
            return ToolResult(
                success=False,
                tool="music_play",
                error="No song or artist specified to play.",
            )

        if provider == "spotify":
            return await self._music_search(args, ctx)

        if provider == "youtube":
            logger.info(f"[AI-BRAIN] _music_play (YouTube): query={query!r}, artist={artist_hint!r}")
            yt_res = youtube_service.search_youtube(
                query=query,
                limit=10,
                artist_hint=artist_hint,
            )
            best = yt_res.get("best_match")
            if yt_res.get("success") and best:
                from app.services.mongo_service import mongo_service
                sid = ctx.session_id if ctx else "anonymous"
                mongo_service.save_music_search_background(
                    session_id=sid,
                    query=query,
                    track_id=best.get("videoId"),
                    title=best.get("title"),
                    artist=best.get("artist"),
                    album=best.get("channelTitle"),
                    spotify_url=best.get("url"),
                )
                return ToolResult(
                    success=True,
                    tool="music_play",
                    data={
                        "query": query,
                        "provider": "youtube",
                        "videoId": best.get("videoId"),
                        "title": best.get("title"),
                        "artist": best.get("artist"),
                        "url": best.get("url"),
                    },
                    track_title=best.get("title"),
                    track_artist=best.get("artist"),
                    track_payload=best,
                )
            err_msg = yt_res.get("message") or f'Could not find "{query}" on YouTube.'
            return ToolResult(
                success=False,
                tool="music_play",
                error=err_msg,
            )

        # Default provider: SoundCloud
        from app.services.soundcloud_service import soundcloud_service
        logger.info(f"[AI-BRAIN] _music_play (SoundCloud): query={query!r}, artist={artist_hint!r}")
        sc_res = soundcloud_service.search_and_resolve_playable(
            query=query,
            artist_hint=artist_hint,
        )

        best = sc_res.get("best_match")
        if sc_res.get("success") and best:
            if best.get("access") == "blocked":
                return ToolResult(
                    success=False,
                    tool="music_play",
                    error="I found the song, but this SoundCloud track is not available for playback.",
                    track_title=best.get("title"),
                    track_artist=best.get("artist"),
                    track_payload=best,
                )

            from app.services.mongo_service import mongo_service
            sid = ctx.session_id if ctx else "anonymous"
            mongo_service.save_music_search_background(
                session_id=sid,
                query=query,
                track_id=best.get("urn") or best.get("id"),
                title=best.get("title"),
                artist=best.get("artist"),
                album=best.get("creator"),
                spotify_url=best.get("permalinkUrl") or best.get("webpage_url"),
            )
            return ToolResult(
                success=True,
                tool="music_play",
                data={
                    "query": query,
                    "provider": "soundcloud",
                    "id": best.get("id"),
                    "urn": best.get("urn"),
                    "title": best.get("title"),
                    "artist": best.get("artist"),
                    "audio_url": best.get("audio_url"),
                    "url": best.get("permalinkUrl") or best.get("webpage_url"),
                },
                track_title=best.get("title"),
                track_artist=best.get("artist"),
                track_payload=best,
            )

        err_msg = sc_res.get("message") or f'I couldn\'t find a playable SoundCloud result for "{query}".'
        return ToolResult(
            success=False,
            tool="music_play",
            error=err_msg,
        )

    async def _soundcloud_search(
        self, args: Dict[str, Any], ctx: Optional[ConversationContext]
    ) -> ToolResult:
        """Search SoundCloud with deterministic ranking."""
        from app.services.soundcloud_service import soundcloud_service
        query = str(args.get("query", "")).strip()
        artist_hint = args.get("artist")
        limit = int(args.get("limit", 10))

        if not query:
            return ToolResult(success=False, tool="soundcloud_search", error="No search query provided.")

        res = soundcloud_service.search_tracks(query=query, artist_hint=artist_hint, limit=limit)
        if res.get("success"):
            best = res.get("best_match")
            return ToolResult(
                success=True,
                tool="soundcloud_search",
                data=res,
                track_title=best.get("title") if best else None,
                track_artist=best.get("artist") if best else None,
                track_payload=best,
            )
        return ToolResult(
            success=False,
            tool="soundcloud_search",
            error=res.get("message", "SoundCloud search returned no results."),
        )

    async def _youtube_search(
        self, args: Dict[str, Any], ctx: Optional[ConversationContext]
    ) -> ToolResult:
        """Search YouTube Data API v3 with deterministic ranking."""
        query = str(args.get("query", "")).strip()
        artist_hint = args.get("artist")
        limit = int(args.get("limit", 10))
        logger.info(f"[AI-BRAIN] _youtube_search: query={query!r}, artist={artist_hint!r}")

        res = youtube_service.search_youtube(
            query=query,
            limit=limit,
            artist_hint=artist_hint,
        )
        if not res.get("success"):
            return ToolResult(
                success=False,
                tool="youtube_search",
                error=res.get("message", "YouTube search failed."),
            )

        best = res.get("best_match")
        return ToolResult(
            success=True,
            tool="youtube_search",
            data={
                "query": query,
                "total": res.get("total", 0),
                "tracks": res.get("tracks", []),
                "best_match": best,
            },
            track_title=best.get("title") if best else None,
            track_artist=best.get("artist") if best else None,
            track_payload=best,
        )

    async def _music_search(
        self, args: Dict[str, Any], ctx: Optional[ConversationContext]
    ) -> ToolResult:
        query = str(args.get("query", "")).strip()
        artist_hint = args.get("artist")
        language_hint = args.get("language")
        logger.info(f"[AI-BRAIN] _music_search: query={query!r}, artist={artist_hint!r}, lang={language_hint!r}")

        # 1. Search Spotify with deterministic ranking & pagination
        sp_res = spotify_service.search_spotify(
            query=query,
            item_type="track",
            limit=10,
            offset=0,
            artist_hint=artist_hint,
            language_hint=language_hint,
        )

        best = sp_res.get("best_match")
        if sp_res.get("success") and best:
            from app.services.mongo_service import mongo_service
            sid = ctx.session_id if ctx else "anonymous"
            mongo_service.save_music_search_background(
                session_id=sid,
                query=query,
                track_id=best.get("id"),
                title=best.get("title"),
                artist=best.get("artist"),
                album=best.get("album"),
                spotify_url=best.get("external_url"),
            )
            return ToolResult(
                success=True,
                tool="music_search",
                data={"query": query, "open_url": best.get("external_url"), "uri": best.get("uri")},
                track_title=best.get("title"),
                track_artist=best.get("artist"),
                track_payload=best,
            )

        # 2. Free music service fallback if Spotify search returned nothing
        try:
            track_info = free_music_service.search_and_extract(query)
            if track_info:
                return ToolResult(
                    success=True,
                    tool="music_search",
                    data={"query": query, "open_url": track_info.get("webpage_url")},
                    track_title=track_info.get("title", query),
                    track_artist=track_info.get("artist", "Unknown Artist"),
                    track_payload=track_info,
                )
        except Exception as exc:
            logger.warning(f"[AI-BRAIN] Free music fallback error: {exc}")

        err_msg = sp_res.get("message") or f"Could not find any song matching \"{query}\"."
        return ToolResult(
            success=False,
            tool="music_search",
            error=err_msg,
        )

    async def _artist_search(
        self, args: Dict[str, Any], ctx: Optional[ConversationContext]
    ) -> ToolResult:
        artist = str(args.get("artist", args.get("query", ""))).strip()
        logger.info(f"[AI-BRAIN] _artist_search: artist={artist!r}")
        return await self._music_search({"query": artist, "artist": artist}, ctx)

    async def _album_search(
        self, args: Dict[str, Any], ctx: Optional[ConversationContext]
    ) -> ToolResult:
        album = str(args.get("album", args.get("query", ""))).strip()
        logger.info(f"[AI-BRAIN] _album_search: album={album!r}")
        return await self._music_search({"query": album, "album": album}, ctx)

    async def _playlist_search(
        self, args: Dict[str, Any], ctx: Optional[ConversationContext]
    ) -> ToolResult:
        query = str(args.get("query", "")).strip()
        logger.info(f"[AI-BRAIN] _playlist_search: query={query!r}")
        return await self._music_search({"query": f"{query} playlist"}, ctx)

    async def _open_spotify(
        self, args: Dict[str, Any], ctx: Optional[ConversationContext]
    ) -> ToolResult:
        query = str(args.get("query", "")).strip()
        logger.info(f"[AI-BRAIN] _open_spotify: query={query!r}")
        return await self._music_search({"query": query}, ctx)

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
            sc_res = soundcloud_service.search_tracks(next_query, limit=10)
            candidates = sc_res.get("tracks", []) if sc_res.get("success") else []
            next_track = None
            for t in candidates:
                if ctx and ctx.last_played_track and t.get("title", "").strip().lower() == ctx.last_played_track.strip().lower():
                    continue
                next_track = t
                break

            if not next_track:
                alt_res = soundcloud_service.search_tracks("popular hits", limit=10)
                if alt_res.get("success") and alt_res.get("tracks"):
                    for t in alt_res["tracks"]:
                        if ctx and ctx.last_played_track and t.get("title", "").strip().lower() == ctx.last_played_track.strip().lower():
                            continue
                        next_track = t
                        break

            if next_track:
                if not next_track.get("audio_url"):
                    stream_url = soundcloud_service.resolve_playable_stream(
                        next_track.get("urn") or str(next_track.get("id"))
                    )
                    if stream_url:
                        next_track["audio_url"] = stream_url

                return ToolResult(
                    success=True,
                    tool="music_next",
                    data={"query": next_query},
                    track_title=next_track.get("title", next_query),
                    track_artist=next_track.get("artist", "Unknown Artist"),
                    track_payload=next_track,
                    action="play",
                )
        except Exception as exc:
            logger.error(f"[AI-BRAIN] music_next search error: {exc}")

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
