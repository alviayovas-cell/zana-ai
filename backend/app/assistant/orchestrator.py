import re
from typing import Optional
from app.schemas.chat import ChatResponse, SuggestionItem, TrackPayload
from app.assistant.commands import CommandAction, ParsedCommand
from app.services.spotify_service import spotify_service
from app.services.free_music_service import free_music_service
from app.core.logging_config import logger




class Orchestrator:
    """
    Central router for Zana assistant.
    Dispatches parsed intents to appropriate tools, Spotify player, or fallback handlers.
    """

    def parse_baseline_intent(self, text: str) -> ParsedCommand:
        # Music Playback: Play
        play_match = re.search(r"^(?:please\s+)?(?:play|listen to|put on)\s+(.+)", text, re.IGNORECASE)
        if play_match:
            song_query = play_match.group(1).strip()
            return ParsedCommand(
                action=CommandAction.MUSIC_SEARCH_PLAY,
                query=song_query,
                parameters={"query": song_query}
            )

        normalized = text.lower().strip()


        # Music Playback: Pause / Stop
        if re.search(r"^(?:pause|stop music|pause song|stop playback|pause playback)\b", normalized):
            return ParsedCommand(action=CommandAction.MUSIC_PAUSE, query=text)

        # Music Playback: Resume / Unpause
        if re.search(r"^(?:resume|unpause|continue playing|continue music)\b", normalized):
            return ParsedCommand(action=CommandAction.MUSIC_RESUME, query=text)

        # Music Playback: Next / Skip
        if re.search(r"^(?:next|skip|next song|skip song|next track)\b", normalized):
            return ParsedCommand(action=CommandAction.MUSIC_NEXT, query=text)

        # Music Playback: Previous / Back
        if re.search(r"^(?:prev|previous|previous song|last song|go back|previous track)\b", normalized):
            return ParsedCommand(action=CommandAction.MUSIC_PREVIOUS, query=text)

        # Music Volume
        vol_match = re.search(r"(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})%?", normalized)
        if vol_match:
            vol_val = int(vol_match.group(1))
            return ParsedCommand(
                action=CommandAction.MUSIC_VOLUME,
                query=text,
                parameters={"volume": vol_val}
            )

        # Greetings
        if re.search(r"^(hi|hello|hey|greetings|hola|namaste)\b", normalized):
            return ParsedCommand(action=CommandAction.GREETING, query=text)

        # Help
        if re.search(r"^(help|what can you do|commands|features)", normalized):
            return ParsedCommand(action=CommandAction.HELP, query=text)

        # Status
        if re.search(r"^(status|system status|ping|are you online)", normalized):
            return ParsedCommand(action=CommandAction.STATUS, query=text)

        # Catch-all
        return ParsedCommand(action=CommandAction.UNKNOWN, query=text)

    async def handle_message(self, message: str, session_id: Optional[str] = None) -> ChatResponse:
        logger.info(f"Processing message: '{message}' (session: {session_id})")
        command = self.parse_baseline_intent(message)

        # Handle Greetings
        if command.action == CommandAction.GREETING:
            return ChatResponse(
                message="Hello! I am Zana, your AI music assistant. How can I help you today?",
                session_id=session_id,
                suggestions=[
                    SuggestionItem(label="Play Blinding Lights", action_type="music_play"),
                    SuggestionItem(label="Check Spotify Status", action_type="status"),
                    SuggestionItem(label="What can you do?", action_type="help"),
                ]
            )

        # Handle Help
        elif command.action == CommandAction.HELP:
            return ChatResponse(
                message=(
                    "🎵 **Zana AI Assistant Capabilities**\n\n"
                    "• **Music Playback**: Say `Play <song/artist>` (e.g. *Play Starboy* or *Play Coldplay*)\n"
                    "• **Controls**: Say `Pause`, `Resume`, `Next song`, `Previous song`\n"
                    "• **Volume**: Say `Set volume to 80` or `Volume 50`\n"
                    "• **Spotify Sync**: Connect your Spotify in the sidebar to stream music seamlessly."
                ),
                session_id=session_id,
                suggestions=[
                    SuggestionItem(label="Play Bohemian Rhapsody", action_type="music_play"),
                    SuggestionItem(label="Pause music", action_type="music_pause"),
                    SuggestionItem(label="Check status", action_type="status"),
                ]
            )

        # Handle Status
        elif command.action == CommandAction.STATUS:
            is_sp_auth = spotify_service.is_authenticated()
            sp_user = spotify_service.get_current_user() if is_sp_auth else None
            user_text = f"Connected as **{sp_user['display_name']}**" if sp_user else "Not connected (Click 'Connect Spotify' in sidebar)"

            return ChatResponse(
                message=(
                    "**System Status**:\n"
                    "• Backend API: `Online` ✅\n"
                    f"• Spotify Service: `{user_text}`\n"
                    "• Ready for playback commands!"
                ),
                session_id=session_id,
                suggestions=[
                    SuggestionItem(label="Play some lo-fi beats", action_type="music_play"),
                    SuggestionItem(label="What can you do?", action_type="help"),
                ]
            )

        # Handle Music Play
        elif command.action == CommandAction.MUSIC_SEARCH_PLAY:
            query = command.parameters.get("query", message)
            logger.info(f"Searching and streaming audio for: '{query}'")

            track_info = free_music_service.search_and_extract(query)
            if track_info and track_info.get("audio_url"):
                payload = TrackPayload(
                    id=track_info.get("id"),
                    title=track_info.get("title", query),
                    artist=track_info.get("artist", "Unknown Artist"),
                    album_art=track_info.get("album_art"),
                    audio_url=track_info.get("audio_url"),
                    duration=track_info.get("duration", 0),
                    webpage_url=track_info.get("webpage_url"),
                )
                return ChatResponse(
                    message=f"🎶 Now streaming **{payload.title}** by **{payload.artist}** directly in your browser!",
                    session_id=session_id,
                    track=payload,
                    suggestions=[
                        SuggestionItem(label="Pause music", action_type="music_pause"),
                        SuggestionItem(label="Play Blinding Lights", action_type="music_play"),
                        SuggestionItem(label="Set volume to 80", action_type="music_volume"),
                    ]
                )
            else:
                # If free extraction failed, try Spotify fallback
                if spotify_service.is_authenticated():
                    res = spotify_service.search_and_play(query)
                    return ChatResponse(
                        message=res.get("message", "Triggered Spotify playback."),
                        session_id=session_id,
                    )
                return ChatResponse(
                    message=f"⚠️ Could not find an audio stream for **\"{query}\"**. Please try another song title or artist!",
                    session_id=session_id,
                    suggestions=[
                        SuggestionItem(label="Play Starboy", action_type="music_play"),
                        SuggestionItem(label="Help", action_type="help"),
                    ]
                )


        # Handle Pause
        elif command.action == CommandAction.MUSIC_PAUSE:
            return ChatResponse(
                message="⏸️ Playback paused.",
                session_id=session_id,
                action="pause",
                suggestions=[
                    SuggestionItem(label="Resume", action_type="music_resume"),
                    SuggestionItem(label="Next song", action_type="music_next"),
                ]
            )

        # Handle Resume
        elif command.action == CommandAction.MUSIC_RESUME:
            return ChatResponse(
                message="▶️ Resuming music playback.",
                session_id=session_id,
                action="resume",
                suggestions=[
                    SuggestionItem(label="Pause", action_type="music_pause"),
                    SuggestionItem(label="Next song", action_type="music_next"),
                ]
            )

        # Handle Next / Skip
        elif command.action == CommandAction.MUSIC_NEXT:
            # Pick a popular track to skip to
            skip_query = "Starboy The Weeknd"
            track_info = free_music_service.search_and_extract(skip_query)
            if track_info:
                payload = TrackPayload(
                    id=track_info.get("id"),
                    title=track_info.get("title", skip_query),
                    artist=track_info.get("artist", "The Weeknd"),
                    album_art=track_info.get("album_art"),
                    audio_url=track_info.get("audio_url"),
                    duration=track_info.get("duration", 0),
                    webpage_url=track_info.get("webpage_url"),
                )
                return ChatResponse(
                    message=f"⏭️ Skipped to next track: **{payload.title}** by **{payload.artist}**",
                    session_id=session_id,
                    track=payload,
                    action="play",
                    suggestions=[
                        SuggestionItem(label="Pause", action_type="music_pause"),
                        SuggestionItem(label="Next song", action_type="music_next"),
                    ]
                )
            return ChatResponse(
                message="⏭️ Skipped track.",
                session_id=session_id,
                action="next",
            )

        # Handle Previous
        elif command.action == CommandAction.MUSIC_PREVIOUS:
            return ChatResponse(
                message="⏮️ Restarting track from the beginning.",
                session_id=session_id,
                action="seek",
                action_value=0,
                suggestions=[
                    SuggestionItem(label="Pause", action_type="music_pause"),
                    SuggestionItem(label="Next song", action_type="music_next"),
                ]
            )

        # Handle Volume
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


        # Fallback / Unknown
        else:
            return ChatResponse(
                message=(
                    f"I received: \"{message}\".\n\n"
                    "Try asking me to play a song! For example:\n"
                    "• *\"Play Shape of You\"*\n"
                    "• *\"Play synthwave music\"*\n"
                    "• *\"Pause\"* or *\"Set volume to 75\"*"
                ),
                session_id=session_id,
                suggestions=[
                    SuggestionItem(label="Play Blinding Lights", action_type="music_play"),
                    SuggestionItem(label="What can you do?", action_type="help"),
                ]
            )


orchestrator = Orchestrator()
