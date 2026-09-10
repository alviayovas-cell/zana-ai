"""
response_generator.py — Builds final ChatResponse from tool results.

Converts ToolResult + IntentResult into a natural, concise ChatResponse.

For general_conversation intents, calls llm_service to generate a reply.
For all other intents, builds a deterministic response from tool output.

Principles:
- Responses are concise and contextual.
- Failures are reported honestly (no fake success).
- Suggestions are context-appropriate.
"""
from __future__ import annotations

from typing import List, Optional

from app.core.config import settings
from app.core.logging_config import logger
from app.schemas.chat import ChatResponse, SuggestionItem, TrackPayload
from app.services.llm_service import llm_service
from app.assistant.brain.tool_executor import ToolResult
from app.assistant.brain.intent_analyzer import IntentResult
from app.assistant.brain.context_manager import ConversationContext


ZANA_PERSONA_PROMPT = (
    "You are Zana, a personal AI music assistant. "
    "Reply helpfully and concisely. Keep responses under 3 sentences. "
    "You can play music, control playback, and have conversations. "
    "Do not mention being an AI unless asked. "
    "Do not invent Spotify results or fake tool executions."
)


# ---------------------------------------------------------------------------
# Suggestion helpers
# ---------------------------------------------------------------------------

def _music_playing_suggestions() -> List[SuggestionItem]:
    return [
        SuggestionItem(label="Pause music", action_type="music_pause"),
        SuggestionItem(label="Next song", action_type="music_next"),
        SuggestionItem(label="Set volume to 70", action_type="music_volume"),
    ]


def _no_music_suggestions() -> List[SuggestionItem]:
    return [
        SuggestionItem(label="Play Blinding Lights", action_type="music_play"),
        SuggestionItem(label="Play relaxing music", action_type="music_play"),
        SuggestionItem(label="What can you do?", action_type="help"),
    ]


def _control_suggestions() -> List[SuggestionItem]:
    return [
        SuggestionItem(label="Pause", action_type="music_pause"),
        SuggestionItem(label="Next song", action_type="music_next"),
        SuggestionItem(label="Resume", action_type="music_resume"),
    ]


# ---------------------------------------------------------------------------
# Response Generator
# ---------------------------------------------------------------------------

class ResponseGenerator:
    """
    Converts a ToolResult + IntentResult into a ChatResponse.

    For conversational intents (general_conversation, assistant_capabilities),
    it calls llm_service to generate a natural reply.
    """

    async def generate(
        self,
        tool_result: ToolResult,
        intent_result: IntentResult,
        original_message: str,
        ctx: Optional[ConversationContext],
        session_id: Optional[str],
    ) -> ChatResponse:
        """
        Build the final ChatResponse.
        """
        intent = intent_result.intent

        logger.info(f"[AI-BRAIN] Generating response for intent={intent!r}, success={tool_result.success}")

        # ── Clarification needed ─────────────────────────────────────────────
        if intent_result.needs_clarification:
            q = intent_result.clarification_question or "Could you be more specific?"
            logger.info(f"[AI-BRAIN] Asking for clarification: {q!r}")
            return ChatResponse(
                message=q,
                session_id=session_id,
                suggestions=_no_music_suggestions(),
                intent=intent,
                confidence=intent_result.confidence,
                tool="clarification",
                execution_status="clarification_needed",
            )

        # ── Tool failure ─────────────────────────────────────────────────────
        if not tool_result.success and tool_result.tool not in (
            "chat_response", "assistant_capabilities", "assistant_status"
        ):
            return self._error_response(tool_result, session_id, intent_result)

        # ── music_play (YouTube Embedded Playback) ───────────────────────────
        if (intent == "music_play" or tool_result.tool == "music_play") and tool_result.success and tool_result.track_payload:
            artist_suffix = f" by **{tool_result.track_artist}**" if tool_result.track_artist else ""
            reply_text = f"Playing **{tool_result.track_title}**{artist_suffix} from YouTube."
            pl_dict = dict(tool_result.track_payload)
            pl_dict["provider"] = pl_dict.get("provider", "youtube")
            payload = TrackPayload(**pl_dict)
            return ChatResponse(
                message=reply_text,
                session_id=session_id,
                track=payload,
                action="play",
                action_value={"provider": payload.provider, "videoId": payload.video_id or payload.id},
                suggestions=[
                    SuggestionItem(label="Pause", action_type="music_pause"),
                    SuggestionItem(label="Next song", action_type="music_next"),
                    SuggestionItem(label="Open on YouTube", action_type="open_youtube", payload=payload.webpage_url),
                ],
                intent=intent,
                confidence=intent_result.confidence,
                tool=tool_result.tool,
                arguments=intent_result.arguments,
                execution_status="success",
            )

        # ── music_search / music_search_play / artist_search / open_spotify ─
        if intent in ("music_search", "music_search_play", "artist_search", "album_search", "playlist_search", "open_spotify") and tool_result.success and tool_result.track_payload:
            artist_suffix = f" by **{tool_result.track_artist}**" if tool_result.track_artist else ""
            reply_text = f"I found **{tool_result.track_title}**{artist_suffix}. Open it in Spotify to listen."
            # Clean dictionary for TrackPayload
            pl_dict = {
                "id": tool_result.track_payload.get("id"),
                "title": tool_result.track_payload.get("title") or tool_result.track_title or "",
                "artist": tool_result.track_payload.get("artist") or tool_result.track_artist or "Unknown Artist",
                "album": tool_result.track_payload.get("album"),
                "album_art": tool_result.track_payload.get("album_art"),
                "audio_url": tool_result.track_payload.get("audio_url"),
                "duration": tool_result.track_payload.get("duration"),
                "duration_ms": tool_result.track_payload.get("duration_ms"),
                "release_date": tool_result.track_payload.get("release_date"),
                "release_year": tool_result.track_payload.get("release_year"),
                "external_url": tool_result.track_payload.get("external_url"),
                "uri": tool_result.track_payload.get("uri"),
                "webpage_url": tool_result.track_payload.get("webpage_url"),
                "ranking_score": tool_result.track_payload.get("ranking_score"),
            }
            return ChatResponse(
                message=reply_text,
                session_id=session_id,
                track=TrackPayload(**pl_dict),
                action=None,  # No direct playback
                suggestions=[
                    SuggestionItem(label="Open in Spotify", action_type="open_spotify", payload=pl_dict.get("external_url")),
                    SuggestionItem(label=f"More by {tool_result.track_artist}", action_type="artist_search", payload=tool_result.track_artist),
                    SuggestionItem(label="Search Tamil songs", action_type="music_search"),
                ],
                intent=intent,
                confidence=intent_result.confidence,
                tool=tool_result.tool,
                arguments=intent_result.arguments,
                execution_status="success",
            )

        # ── music_next ───────────────────────────────────────────────────────
        if intent == "music_next" and tool_result.success and tool_result.track_payload:
            return ChatResponse(
                message=f"⏭️ Next track: **{tool_result.track_title}** by **{tool_result.track_artist}**. Open it in Spotify to listen.",
                session_id=session_id,
                track=TrackPayload(**tool_result.track_payload),
                action=None,
                suggestions=_control_suggestions(),
                intent=intent,
                confidence=intent_result.confidence,
                tool=tool_result.tool,
                arguments=intent_result.arguments,
                execution_status="success",
            )

        # ── music_pause ──────────────────────────────────────────────────────
        if intent == "music_pause" and tool_result.success:
            return ChatResponse(
                message="⏸️ Paused.",
                session_id=session_id,
                action="pause",
                suggestions=[
                    SuggestionItem(label="Resume", action_type="music_resume"),
                    SuggestionItem(label="Next song", action_type="music_next"),
                ],
                intent=intent,
                confidence=intent_result.confidence,
                tool=tool_result.tool,
                execution_status="success",
            )

        # ── music_resume ─────────────────────────────────────────────────────
        if intent == "music_resume" and tool_result.success:
            return ChatResponse(
                message="▶️ Resuming playback.",
                session_id=session_id,
                action="resume",
                suggestions=_control_suggestions(),
                intent=intent,
                confidence=intent_result.confidence,
                tool=tool_result.tool,
                execution_status="success",
            )

        # ── music_previous ───────────────────────────────────────────────────
        if intent == "music_previous" and tool_result.success:
            return ChatResponse(
                message="⏮️ Restarting track from the beginning.",
                session_id=session_id,
                action=tool_result.action,
                action_value=tool_result.action_value,
                suggestions=_control_suggestions(),
                intent=intent,
                confidence=intent_result.confidence,
                tool=tool_result.tool,
                execution_status="success",
            )

        # ── music_volume ─────────────────────────────────────────────────────
        if intent == "music_volume" and tool_result.success:
            vol_pct = int((tool_result.action_value or 0.75) * 100)
            return ChatResponse(
                message=f"🔊 Volume set to **{vol_pct}%**.",
                session_id=session_id,
                action=tool_result.action,
                action_value=tool_result.action_value,
                suggestions=_control_suggestions(),
                intent=intent,
                confidence=intent_result.confidence,
                tool=tool_result.tool,
                arguments=intent_result.arguments,
                execution_status="success",
            )

        # ── music_current_track ──────────────────────────────────────────────
        if intent == "music_current_track":
            return self._current_track_response(tool_result, session_id, intent_result)

        # ── assistant_capabilities ───────────────────────────────────────────
        if intent == "assistant_capabilities":
            return ChatResponse(
                message=(
                    "🎵 **Here's what I can do:**\n\n"
                    "• **Play music** — *\"Play Believer\"* or *\"Play lo-fi beats\"*\n"
                    "• **Playback control** — Pause, Resume, Next, Previous\n"
                    "• **Volume** — *\"Set volume to 60\"*\n"
                    "• **Current track** — *\"What's playing?\"*\n"
                    "• **Voice commands** — Click the 🎤 mic and speak!\n"
                    "• **Natural conversation** — Just chat with me!"
                ),
                session_id=session_id,
                suggestions=[
                    SuggestionItem(label="Play Blinding Lights", action_type="music_play"),
                    SuggestionItem(label="What's playing?", action_type="music_current_track"),
                    SuggestionItem(label="Check status", action_type="status"),
                ],
                intent=intent,
                confidence=intent_result.confidence,
                tool="assistant_capabilities",
                execution_status="success",
            )

        # ── assistant_status ─────────────────────────────────────────────────
        if intent == "assistant_status":
            from app.services.spotify_service import spotify_service
            sp_auth = spotify_service.is_authenticated()
            sp_user = spotify_service.get_current_user() if sp_auth else None
            user_text = (
                f"Connected as **{sp_user['display_name']}**"
                if sp_user
                else "Not connected"
            )
            provider_info = llm_service.get_provider_info()
            llm_text = f"{provider_info['provider'].upper()} ({provider_info['model']})" if provider_info['configured'] else "Rule-based fallback"

            return ChatResponse(
                message=(
                    "**System Status**\n"
                    "• Backend: `Online` ✅\n"
                    f"• LLM Engine: `{llm_text}`\n"
                    f"• Spotify: {user_text}\n"
                    "• Free Audio Engine: `Active` ✅"
                ),
                session_id=session_id,
                suggestions=_no_music_suggestions(),
                intent=intent,
                confidence=intent_result.confidence,
                tool="assistant_status",
                execution_status="success",
            )

        # ── general_conversation ─────────────────────────────────────────────
        if intent in ("general_conversation", "unknown", "chat_response") or not intent_result.requires_tool:
            return await self._llm_conversation_response(
                original_message, ctx, session_id, intent_result
            )

        # ── Fallback ─────────────────────────────────────────────────────────
        fallback_hint = intent_result.response_hint
        if fallback_hint:
            return ChatResponse(
                message=fallback_hint,
                session_id=session_id,
                suggestions=_no_music_suggestions(),
                intent=intent,
                confidence=intent_result.confidence,
                tool="chat_response",
                execution_status="success",
            )

        return await self._llm_conversation_response(original_message, ctx, session_id, intent_result)

    # ── Sub-methods ──────────────────────────────────────────────────────────

    def _error_response(
        self, tool_result: ToolResult, session_id: Optional[str], intent_result: IntentResult
    ) -> ChatResponse:
        """Return a graceful, honest error message."""
        tool_friendly = {
            "music_search_play": "start playback",
            "music_next": "skip to the next track",
            "music_previous": "go to the previous track",
            "music_volume": "adjust the volume",
            "music_current_track": "retrieve the current track",
        }
        action = tool_friendly.get(tool_result.tool, "complete that action")
        err = tool_result.error or "Something went wrong."

        if "stream" in err.lower() or "find" in err.lower():
            msg = f"⚠️ {err} Try a different song title or artist!"
        elif "volume" in err.lower():
            msg = f"⚠️ {err}"
        else:
            msg = f"⚠️ I couldn't {action} right now. {err}"

        logger.info(f"[AI-BRAIN] Error response: {msg[:80]}")
        return ChatResponse(
            message=msg,
            session_id=session_id,
            status="error",
            suggestions=_no_music_suggestions(),
            intent=intent_result.intent,
            confidence=intent_result.confidence,
            tool=tool_result.tool,
            arguments=intent_result.arguments,
            execution_status="failed",
        )

    def _current_track_response(
        self, result: ToolResult, session_id: Optional[str], intent_result: IntentResult
    ) -> ChatResponse:
        """Format a response for the music_current_track tool."""
        if not result.success:
            return ChatResponse(
                message="🎵 Nothing is currently playing. Want me to play something?",
                session_id=session_id,
                suggestions=_no_music_suggestions(),
                intent=intent_result.intent,
                confidence=intent_result.confidence,
                tool=result.tool,
                execution_status="no_track_playing",
            )

        data = result.data
        source = data.get("source", "context")
        track = data.get("track_name") or result.track_title
        artist = data.get("artists") or result.track_artist

        if track and artist:
            msg = f"🎵 Currently playing: **{track}** by **{artist}**"
        elif track:
            msg = f"🎵 Currently playing: **{track}**"
        elif source == "context" and data.get("query"):
            msg = f"🎵 Last played: songs matching **{data['query']}**"
        else:
            msg = "🎵 I'm not sure what's playing right now."

        return ChatResponse(
            message=msg,
            session_id=session_id,
            suggestions=_control_suggestions(),
            intent=intent_result.intent,
            confidence=intent_result.confidence,
            tool=result.tool,
            arguments={"source": source, "track": track, "artist": artist},
            execution_status="success",
        )

    async def _llm_conversation_response(
        self,
        message: str,
        ctx: Optional[ConversationContext],
        session_id: Optional[str],
        intent_result: IntentResult,
    ) -> ChatResponse:
        """
        Generate a natural conversational reply via llm_service.
        Falls back to fallback_hint if LLM is unavailable.
        """
        fallback_hint = intent_result.response_hint

        if not llm_service.is_configured():
            reply = (
                fallback_hint
                or "I'm here to help! You can ask me to play music or control playback."
            )
            return ChatResponse(
                message=reply,
                session_id=session_id,
                suggestions=_no_music_suggestions(),
                intent=intent_result.intent,
                confidence=intent_result.confidence,
                tool="chat_response",
                execution_status="fallback_no_llm_key",
            )

        # Build message history for LLM context
        messages = [{"role": "system", "content": ZANA_PERSONA_PROMPT}]

        if ctx:
            history = ctx.get_history_for_llm()
            if history and history[-1].get("role") == "user":
                history = history[:-1]
            messages.extend(history)

        messages.append({"role": "user", "content": message})

        reply = await llm_service.generate_text(messages, temperature=0.7)

        if reply:
            logger.info(f"[AI-BRAIN] LLM conversation reply: {reply[:80]!r}")
            return ChatResponse(
                message=reply,
                session_id=session_id,
                suggestions=_no_music_suggestions(),
                intent=intent_result.intent,
                confidence=intent_result.confidence,
                tool="chat_response",
                execution_status="success",
            )

        # Fallback if generation returned None
        fallback = fallback_hint or "I'm not sure about that, but I can help you play music!"
        return ChatResponse(
            message=fallback,
            session_id=session_id,
            suggestions=_no_music_suggestions(),
            intent=intent_result.intent,
            confidence=intent_result.confidence,
            tool="chat_response",
            execution_status="fallback_error",
        )


# Singleton instance
response_generator = ResponseGenerator()
