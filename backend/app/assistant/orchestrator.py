"""
orchestrator.py — Central message router for Zana assistant.

Phase 1–3: Regex fast-path for deterministic commands.
Phase 4:   AI Brain for all UNKNOWN/complex intents.

Flow:
    handle_message()
        ↓
    parse_baseline_intent()   ← fast regex (no LLM, no AI)
        ↓ deterministic commands → handler → ChatResponse
        ↓ UNKNOWN → ai_brain.process() → ChatResponse

The AI Brain updates conversation context internally.
The orchestrator also updates context for regex-handled commands
so that follow-up requests ("next one", "pause") remain context-aware.
"""
import re
from typing import Optional

from app.schemas.chat import ChatResponse, SuggestionItem, TrackPayload
from app.assistant.commands import CommandAction, ParsedCommand
from app.services.spotify_service import spotify_service
from app.services.free_music_service import free_music_service
from app.core.logging_config import logger

# Phase 4: AI Brain + context manager
from app.assistant.brain.brain import ai_brain
from app.assistant.brain.context_manager import context_manager


from app.assistant.fast_router import fast_router

class Orchestrator:
    """
    Central router for Zana assistant.
    Dispatches parsed intents to appropriate tools, Spotify player, or AI Brain.
    """

    def parse_baseline_intent(self, text: str) -> ParsedCommand:
        # First evaluate Fast Command Router
        fast_res = fast_router.route(text)
        if fast_res.matched:
            return fast_res.to_parsed_command()

        # Music Playback: Play regex
        play_match = re.search(r"^(?:please\s+)?(?:play|listen to|put on)\s+(.+)", text, re.IGNORECASE)
        if play_match:
            song_query = play_match.group(1).strip()
            return ParsedCommand(
                action=CommandAction.MUSIC_SEARCH_PLAY,
                query=song_query,
                parameters={"query": song_query}
            )

        return ParsedCommand(action=CommandAction.UNKNOWN, query=text)

    async def handle_message(self, message: str, session_id: Optional[str] = None) -> ChatResponse:
        logger.info(f"Processing message: '{message}' (session: {session_id})")
        command = self.parse_baseline_intent(message)

        # Convenience: session id for context updates
        sid = session_id or "anonymous"

        # ── Handle Greetings ─────────────────────────────────────────────────
        if command.action == CommandAction.GREETING:
            ctx = context_manager.get_or_create(sid)
            ctx.add_user_message(message)
            reply = "Hello! I am Zana, your AI music assistant. How can I help you today?"
            ctx.add_assistant_message(reply)
            return ChatResponse(
                message=reply,
                session_id=session_id,
                suggestions=[
                    SuggestionItem(label="Play Blinding Lights", action_type="music_play"),
                    SuggestionItem(label="Check Spotify Status", action_type="status"),
                    SuggestionItem(label="What can you do?", action_type="help"),
                ]
            )

        # ── Handle Help ──────────────────────────────────────────────────────
        elif command.action == CommandAction.HELP:
            ctx = context_manager.get_or_create(sid)
            ctx.add_user_message(message)
            reply = (
                "🎵 **Zana AI Assistant Capabilities**\n\n"
                "• **Music Playback**: Say `Play <song/artist>` (e.g. *Play Starboy* or *Play Coldplay*)\n"
                "• **Controls**: Say `Pause`, `Resume`, `Next song`, `Previous song`\n"
                "• **Volume**: Say `Set volume to 80` or `Volume 50`\n"
                "• **Current track**: Ask *\"What's playing?\"* or *\"Who sings this?\"*\n"
                "• **Natural language**: Ask me anything — I'll understand!\n"
                "• **Voice**: Click the 🎤 mic and speak your command!\n"
                "• **Spotify Sync**: Connect your Spotify in the sidebar."
            )
            ctx.add_assistant_message(reply)
            return ChatResponse(
                message=reply,
                session_id=session_id,
                suggestions=[
                    SuggestionItem(label="Play Bohemian Rhapsody", action_type="music_play"),
                    SuggestionItem(label="Pause music", action_type="music_pause"),
                    SuggestionItem(label="Check status", action_type="status"),
                ]
            )

        # ── Handle Status ────────────────────────────────────────────────────
        elif command.action == CommandAction.STATUS:
            is_sp_auth = spotify_service.is_authenticated()
            sp_user = spotify_service.get_current_user() if is_sp_auth else None
            user_text = f"Connected as **{sp_user['display_name']}**" if sp_user else "Not connected (Click 'Connect Spotify' in sidebar)"

            return ChatResponse(
                message=(
                    "**System Status**:\n"
                    "• Backend API: `Online` ✅\n"
                    f"• Spotify Service: `{user_text}`\n"
                    "• AI Brain: `Active` 🧠\n"
                    "• Ready for playback commands!"
                ),
                session_id=session_id,
                suggestions=[
                    SuggestionItem(label="Play some lo-fi beats", action_type="music_play"),
                    SuggestionItem(label="What can you do?", action_type="help"),
                ]
            )

        # ── Handle Music Play (YouTube Provider embedded playback) ───────────
        elif command.action in (CommandAction.MUSIC_PLAY, CommandAction.YOUTUBE_PLAY):
            query = command.parameters.get("query") or command.query or message
            artist_hint = command.parameters.get("artist")
            provider = command.parameters.get("provider", "youtube")
            logger.info(f"[ORCH] Music playback on {provider}: '{query}' (artist={artist_hint!r})")

            ctx = context_manager.get_or_create(sid)
            ctx.add_user_message(message)
            ctx.update_music_context(query=query, artist=artist_hint)

            if command.parameters.get("context_play") or query.lower().strip() in ("this", "it", "current song", "current track", "play on youtube", "play this on youtube"):
                if ctx.has_music_context() and ctx.last_played_track:
                    query = f"{ctx.last_played_track} {ctx.last_played_artist or ''}".strip()
                    artist_hint = ctx.last_played_artist or artist_hint

            from app.services.youtube_service import youtube_service
            yt_res = youtube_service.search_youtube(
                query=query,
                limit=10,
                artist_hint=artist_hint,
            )

            if yt_res.get("success") and yt_res.get("best_match"):
                best = yt_res["best_match"]
                from app.services.mongo_service import mongo_service
                mongo_service.save_music_search_background(
                    session_id=sid,
                    query=query,
                    track_id=best.get("videoId"),
                    title=best.get("title"),
                    artist=best.get("artist"),
                    album=best.get("channelTitle"),
                    spotify_url=best.get("url"),
                )

                payload = TrackPayload(**best)
                ctx.update_music_context(
                    query=query,
                    track=payload.title,
                    artist=payload.artist,
                )

                artist_text = f" by **{payload.artist}**" if payload.artist else ""
                reply = f"Playing **{payload.title}**{artist_text} from YouTube."
                ctx.add_assistant_message(reply)

                return ChatResponse(
                    message=reply,
                    session_id=session_id,
                    track=payload,
                    action="play",
                    action_value={"provider": "youtube", "videoId": payload.video_id or payload.id},
                    intent="music_play",
                    confidence=0.98,
                    tool="music_play",
                    execution_status="success",
                    suggestions=[
                        SuggestionItem(label="Pause", action_type="music_pause"),
                        SuggestionItem(label="Next song", action_type="music_next"),
                        SuggestionItem(label="Open on YouTube", action_type="open_youtube", payload=payload.webpage_url),
                    ]
                )
            else:
                err_msg = yt_res.get("message") or f'Could not find "{query}" on YouTube.'
                ctx.add_assistant_message(err_msg)
                return ChatResponse(
                    message=err_msg,
                    session_id=session_id,
                    intent="music_play",
                    confidence=0.98,
                    tool="music_play",
                    execution_status="failed",
                    suggestions=[
                        SuggestionItem(label="Search on Spotify", action_type="music_search"),
                        SuggestionItem(label="Try another song", action_type="music_play"),
                    ]
                )

        # ── Handle Music Discovery / Search / Spotify Launcher ───────────────
        elif command.action in (
            CommandAction.MUSIC_SEARCH,
            CommandAction.MUSIC_SEARCH_PLAY,
            CommandAction.ARTIST_SEARCH,
            CommandAction.OPEN_SPOTIFY,
        ):
            query = command.parameters.get("query") or command.query or message
            artist_hint = command.parameters.get("artist")
            track_hint = command.parameters.get("track")
            logger.info(f"[ORCH] Music discovery for: '{query}' (artist={artist_hint!r})")

            # Update context
            ctx = context_manager.get_or_create(sid)
            ctx.add_user_message(message)

            # Detect language hint (e.g. Tamil)
            from app.services.multilingual_service import multilingual_service
            lang_code = multilingual_service.detect_language(query)
            lang_hint = "Tamil" if lang_code == "ta" else ("Hindi" if lang_code == "hi" else None)

            # Search Spotify first with deterministic ranking & pagination
            sp_res = spotify_service.search_spotify(
                query=query,
                item_type="track",
                limit=10,
                offset=0,
                artist_hint=artist_hint,
                language_hint=lang_hint,
            )

            best_track = sp_res.get("best_match")
            if sp_res.get("success") and best_track:
                # Save search history to MongoDB
                from app.services.mongo_service import mongo_service
                mongo_service.save_music_search_background(
                    session_id=sid,
                    query=query,
                    track_id=best_track.get("id"),
                    title=best_track.get("title"),
                    artist=best_track.get("artist"),
                    album=best_track.get("album"),
                    spotify_url=best_track.get("external_url"),
                )

                payload = TrackPayload(**best_track)
                ctx.update_music_context(
                    query=query,
                    track=payload.title,
                    artist=payload.artist,
                )

                artist_text = f" by **{payload.artist}**" if payload.artist else ""
                reply = f"I found **{payload.title}**{artist_text}. Open it in Spotify to listen."
                ctx.add_assistant_message(reply)

                return ChatResponse(
                    message=reply,
                    session_id=session_id,
                    track=payload,
                    action=None,  # Free mode: no fake playback
                    intent="music_search",
                    confidence=0.98,
                    tool="music_search",
                    execution_status="success",
                    suggestions=[
                        SuggestionItem(label="Open in Spotify", action_type="open_spotify", payload=payload.external_url),
                        SuggestionItem(label=f"More by {payload.artist}", action_type="artist_search", payload=payload.artist),
                        SuggestionItem(label="Search Tamil songs", action_type="music_search"),
                    ]
                )

            # Fallback: Free music service if Spotify search returned no results
            track_info = free_music_service.search_and_extract(query)
            if track_info:
                payload = TrackPayload(
                    id=track_info.get("id"),
                    title=track_info.get("title", query),
                    artist=track_info.get("artist", "Unknown Artist"),
                    album_art=track_info.get("album_art"),
                    audio_url=track_info.get("audio_url"),
                    duration=track_info.get("duration", 0),
                    webpage_url=track_info.get("webpage_url"),
                )
                ctx.update_music_context(
                    query=query,
                    track=payload.title,
                    artist=payload.artist,
                )
                reply = f"I found **{payload.title}** by **{payload.artist}**. Open it in Spotify to listen."
                ctx.add_assistant_message(reply)
                return ChatResponse(
                    message=reply,
                    session_id=session_id,
                    track=payload,
                    action=None,
                    intent="music_search",
                    confidence=0.9,
                    tool="music_search",
                    execution_status="success",
                    suggestions=[
                        SuggestionItem(label="Search Tamil songs", action_type="music_search"),
                        SuggestionItem(label="What can you do?", action_type="help"),
                    ]
                )

            reply = f"Could not find any song matching **\"{query}\"**. Please try another title or artist!"
            ctx.add_assistant_message(reply)
            return ChatResponse(
                message=reply,
                session_id=session_id,
                suggestions=[
                    SuggestionItem(label="Search Pattuma", action_type="music_search"),
                    SuggestionItem(label="Search Tamil songs", action_type="music_search"),
                    SuggestionItem(label="Help", action_type="help"),
                ]
            )

        # ── Handle Pause ─────────────────────────────────────────────────────
        elif command.action == CommandAction.MUSIC_PAUSE:
            ctx = context_manager.get_or_create(sid)
            ctx.add_user_message(message)
            reply = "⏸️ Playback paused."
            ctx.add_assistant_message(reply)
            return ChatResponse(
                message=reply,
                session_id=session_id,
                action="pause",
                suggestions=[
                    SuggestionItem(label="Resume", action_type="music_resume"),
                    SuggestionItem(label="Next song", action_type="music_next"),
                ]
            )

        # ── Handle Resume ────────────────────────────────────────────────────
        elif command.action == CommandAction.MUSIC_RESUME:
            ctx = context_manager.get_or_create(sid)
            ctx.add_user_message(message)
            reply = "▶️ Resuming music playback."
            ctx.add_assistant_message(reply)
            return ChatResponse(
                message=reply,
                session_id=session_id,
                action="resume",
                suggestions=[
                    SuggestionItem(label="Pause", action_type="music_pause"),
                    SuggestionItem(label="Next song", action_type="music_next"),
                ]
            )

        # ── Handle Next / Skip ───────────────────────────────────────────────
        elif command.action == CommandAction.MUSIC_NEXT:
            ctx = context_manager.get_or_create(sid)
            ctx.add_user_message(message)

            # Context-aware next: use last played artist/query if available
            next_query = None
            if ctx.has_music_context():
                if ctx.last_played_artist and ctx.last_played_artist != "Unknown Artist":
                    next_query = ctx.last_played_artist
                elif ctx.last_played_query:
                    next_query = ctx.last_played_query
            if not next_query:
                next_query = "popular hits"

            logger.info(f"[ORCH] Next track: searching for '{next_query}'")
            track_info = free_music_service.search_and_extract(next_query)
            if track_info and track_info.get("audio_url"):
                payload = TrackPayload(
                    id=track_info.get("id"),
                    title=track_info.get("title", next_query),
                    artist=track_info.get("artist", "Unknown Artist"),
                    album_art=track_info.get("album_art"),
                    audio_url=track_info.get("audio_url"),
                    duration=track_info.get("duration", 0),
                    webpage_url=track_info.get("webpage_url"),
                )
                ctx.update_music_context(
                    query=next_query,
                    track=payload.title,
                    artist=payload.artist,
                )
                reply = f"⏭️ Playing next: **{payload.title}** by **{payload.artist}**"
                ctx.add_assistant_message(reply)
                return ChatResponse(
                    message=reply,
                    session_id=session_id,
                    track=payload,
                    action="play",
                    suggestions=[
                        SuggestionItem(label="Pause", action_type="music_pause"),
                        SuggestionItem(label="Next song", action_type="music_next"),
                    ]
                )
            reply = "⏭️ Skipped track."
            ctx.add_assistant_message(reply)
            return ChatResponse(
                message=reply,
                session_id=session_id,
                action="next",
            )

        # ── Handle Previous ──────────────────────────────────────────────────
        elif command.action == CommandAction.MUSIC_PREVIOUS:
            ctx = context_manager.get_or_create(sid)
            ctx.add_user_message(message)
            reply = "⏮️ Restarting track from the beginning."
            ctx.add_assistant_message(reply)
            return ChatResponse(
                message=reply,
                session_id=session_id,
                action="seek",
                action_value=0,
                suggestions=[
                    SuggestionItem(label="Pause", action_type="music_pause"),
                    SuggestionItem(label="Next song", action_type="music_next"),
                ]
            )

        # ── Handle Volume ────────────────────────────────────────────────────
        elif command.action == CommandAction.MUSIC_VOLUME:
            vol = command.parameters.get("volume", 75)
            clamped = max(0, min(100, vol))
            return ChatResponse(
                message=f"🔊 Volume adjusted to **{clamped}%**.",
                session_id=session_id,
                action="volume",
                action_value=clamped / 100.0,
                suggestions=[
                    SuggestionItem(label="Pause", action_type="music_pause"),
                    SuggestionItem(label="Next song", action_type="music_next"),
                ]
            )

        # ── Handle Current Track ─────────────────────────────────────────────
        elif command.action == CommandAction.MUSIC_CURRENT_TRACK:
            ctx = context_manager.get_or_create(sid)
            ctx.add_user_message(message)

            if spotify_service.is_authenticated():
                try:
                    state = spotify_service.get_playback_state()
                    track = state.get("track")
                    if track and state.get("is_playing"):
                        reply = f"🎵 Currently playing: **{track.get('name')}** by **{track.get('artists')}**"
                        ctx.add_assistant_message(reply)
                        return ChatResponse(
                            message=reply,
                            session_id=session_id,
                            suggestions=[
                                SuggestionItem(label="Pause", action_type="music_pause"),
                                SuggestionItem(label="Next song", action_type="music_next"),
                            ]
                        )
                except Exception:
                    pass

            if ctx.has_music_context():
                track_name = ctx.last_played_track or ctx.last_played_query
                artist_name = ctx.last_played_artist or ""
                reply = f"🎵 Currently playing: **{track_name}**" + (f" by **{artist_name}**" if artist_name else "")
                ctx.add_assistant_message(reply)
                return ChatResponse(
                    message=reply,
                    session_id=session_id,
                    suggestions=[
                        SuggestionItem(label="Pause", action_type="music_pause"),
                        SuggestionItem(label="Next song", action_type="music_next"),
                    ]
                )

            reply = "🎵 Nothing is currently playing. Want me to play a song?"
            ctx.add_assistant_message(reply)
            return ChatResponse(
                message=reply,
                session_id=session_id,
                suggestions=[
                    SuggestionItem(label="Play Blinding Lights", action_type="music_play"),
                    SuggestionItem(label="Play relaxing music", action_type="music_play"),
                ]
            )

        # ── UNKNOWN → AI Brain ───────────────────────────────────────────────
        else:
            logger.info(f"[ORCH] UNKNOWN intent → delegating to AI Brain")
            return await ai_brain.process(
                message=message,
                session_id=session_id,
            )


orchestrator = Orchestrator()
