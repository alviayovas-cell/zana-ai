"""
intent_analyzer.py — LLM-powered intent understanding for Zana AI Brain.

Architecture:
    1. FAST PRE-CHECK: Context-aware shortcuts that don't call the LLM.
       (e.g. "next one" when music is playing → music_next directly)

    2. LLM ANALYSIS: Uses llm_service to analyze user message + conversation history
       + long-term memory, returning structured JSON output.

    3. FALLBACK: If LLM is unavailable or returns invalid JSON, falls back
       to a safe rule-based intent resolution.

LLM provider: Unified via llm_service (supports OpenAI and Groq).
Output format: structured JSON (no fragile text parsing).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logging_config import logger
from app.services.llm_service import llm_service
from app.assistant.brain.context_manager import ConversationContext


# ---------------------------------------------------------------------------
# Data model for a parsed intent
# ---------------------------------------------------------------------------

class IntentResult:
    """Structured output from the intent analyzer."""

    __slots__ = (
        "intent",
        "confidence",
        "requires_tool",
        "tool",
        "arguments",
        "needs_clarification",
        "clarification_question",
        "response_hint",
        "steps",
    )

    def __init__(
        self,
        intent: str = "general_conversation",
        confidence: float = 0.8,
        requires_tool: bool = False,
        tool: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        needs_clarification: bool = False,
        clarification_question: Optional[str] = None,
        response_hint: Optional[str] = None,
        steps: Optional[list] = None,
    ) -> None:
        self.intent = intent
        self.confidence = confidence
        self.requires_tool = requires_tool
        self.tool = tool
        self.arguments = arguments or {}
        self.needs_clarification = needs_clarification
        self.clarification_question = clarification_question
        self.response_hint = response_hint
        self.steps = steps or []

    def __repr__(self) -> str:
        return (
            f"IntentResult(intent={self.intent!r}, confidence={self.confidence}, "
            f"tool={self.tool!r}, args={self.arguments}, clarify={self.needs_clarification})"
        )


# ---------------------------------------------------------------------------
# Fast pre-check patterns (no LLM needed)
# ---------------------------------------------------------------------------

# Context-aware follow-up patterns
_NEXT_PATTERNS = re.compile(
    r"^(next one|next track|skip this|skip it|another one|play another|play next|"
    r"something else|next please|next song please)\b",
    re.IGNORECASE,
)
_PREV_PATTERNS = re.compile(
    r"^(previous one|go back|last one|play that again|replay)\b",
    re.IGNORECASE,
)
_WHAT_PLAYING_PATTERNS = re.compile(
    r"(what'?s? (playing|on|this song)|what song|which song|what (are we|am i) listening|"
    r"name of (this|the) song|who (sings|sang|is singing|is this)|"
    r"tell me (about|more about) this song|this track|current(ly playing)?)",
    re.IGNORECASE,
)
_SIMILAR_PATTERNS = re.compile(
    r"^(something (more|similar|like this)|more like (this|that)|"
    r"play (something|more) (like|similar)|another (one )?like (this|that))\b",
    re.IGNORECASE,
)
_ENERGETIC_PATTERNS = re.compile(
    r"(more energetic|more upbeat|something faster|pump (it )?up|"
    r"something (more )?energeti|upbeat|hype|workout|gym)\b",
    re.IGNORECASE,
)
_CALM_PATTERNS = re.compile(
    r"(more calm|more relaxing|slow it down|chill|mellow|peaceful|lo.?fi|lofi)\b",
    re.IGNORECASE,
)


def _fast_context_check(
    message: str,
    ctx: Optional[ConversationContext],
) -> Optional[IntentResult]:
    """
    Return an IntentResult without calling the LLM if we can determine intent
    from context + simple pattern matching. Return None to proceed to LLM.
    """
    norm = message.strip()

    # "next one / skip this" when music is playing
    if _NEXT_PATTERNS.match(norm):
        logger.info("[AI-BRAIN] Fast-path: MUSIC_NEXT (context-aware next)")
        return IntentResult(
            intent="music_next",
            confidence=0.98,
            requires_tool=True,
            tool="music_next",
        )

    # "previous / go back"
    if _PREV_PATTERNS.match(norm):
        logger.info("[AI-BRAIN] Fast-path: MUSIC_PREVIOUS (context-aware)")
        return IntentResult(
            intent="music_previous",
            confidence=0.98,
            requires_tool=True,
            tool="music_previous",
        )

    # "what's playing / who sings this"
    if _WHAT_PLAYING_PATTERNS.search(norm):
        logger.info("[AI-BRAIN] Fast-path: MUSIC_CURRENT_TRACK")
        return IntentResult(
            intent="music_current_track",
            confidence=0.95,
            requires_tool=True,
            tool="music_current_track",
        )

    # "something more energetic" — context-aware play request
    if ctx and ctx.has_music_context() and _ENERGETIC_PATTERNS.search(norm):
        logger.info("[AI-BRAIN] Fast-path: MUSIC_PLAY (energetic variant)")
        return IntentResult(
            intent="music_search_play",
            confidence=0.90,
            requires_tool=True,
            tool="music_search_play",
            arguments={"query": "energetic upbeat songs"},
        )

    # "something more calm/relaxing" — context-aware
    if ctx and ctx.has_music_context() and _CALM_PATTERNS.search(norm):
        logger.info("[AI-BRAIN] Fast-path: MUSIC_PLAY (calm variant)")
        return IntentResult(
            intent="music_search_play",
            confidence=0.90,
            requires_tool=True,
            tool="music_search_play",
            arguments={"query": "relaxing calm chill music"},
        )

    # "something similar / another like this" — use last played context
    if ctx and ctx.has_music_context() and _SIMILAR_PATTERNS.match(norm):
        base_query = ctx.last_played_artist or ctx.last_played_query or "popular songs"
        logger.info(f"[AI-BRAIN] Fast-path: MUSIC_PLAY (similar to {base_query!r})")
        return IntentResult(
            intent="music_search_play",
            confidence=0.88,
            requires_tool=True,
            tool="music_search_play",
            arguments={"query": f"songs similar to {base_query}"},
        )

    return None  # → proceed to LLM


# ---------------------------------------------------------------------------
# LLM-based intent analysis
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Zana's intent classification engine. Analyze the user's message and return ONLY valid JSON.

Available intents:
- music_play: user wants to play a song/music video directly (defaults to YouTube playback, e.g. "play Pattuma", "play on YouTube", "listen to Believer")
- music_search: user wants to find, search for songs, mood, genre, or topic (e.g. "search Tamil songs", "find songs by Rahman")
- artist_search: user wants to find songs by a specific artist
- album_search: user wants to find an album
- playlist_search: user wants to find a playlist
- open_spotify: user explicitly wants to open a song/artist in Spotify
- music_pause: user wants to pause/stop music
- music_resume: user wants to resume/continue music
- music_next: user wants to skip to next track
- music_previous: user wants to go to previous track
- music_volume: user wants to change volume (extract percentage 0-100)
- music_current_track: user asks what is playing / who is the artist / info about current track
- general_conversation: user is having a general chat (not music-related)
- assistant_capabilities: user asks what Zana can do / how to use Zana
- assistant_status: user asks about system status / connection
- unknown: cannot determine intent

Rules:
1. For music_play, extract into "arguments":
   - "query": full query string (e.g. "Pattuma by Sai Abhyankkar")
   - "track": specific track title if identified (e.g. "Pattuma"), else null
   - "artist": artist name if identified (e.g. "Sai Abhyankkar"), else null
   - "provider": "youtube" (default) or "spotify" if explicitly mentioned
   Set requires_tool=true, tool="music_play".
2. For music_search, extract "query", "artist", "language", set requires_tool=true, tool="music_search".
3. For artist_search, extract "artist" and set tool="artist_search".
4. For album_search, extract "album" and "artist", set tool="album_search".
5. For open_spotify, extract "query" and set tool="open_spotify".
5. For music_volume, extract "volume" argument as integer 0-100.
6. Keep response_hint short and natural (max 15 words).
7. confidence should reflect certainty (0.0-1.0).

Return ONLY this JSON structure, no other text:
{
  "intent": "<intent_name>",
  "confidence": <float>,
  "requires_tool": <bool>,
  "tool": "<tool_name or null>",
  "arguments": {},
  "needs_clarification": <bool>,
  "clarification_question": "<string or null>",
  "response_hint": "<short natural response or null>",
  "steps": []
}"""


def _build_user_prompt(
    message: str,
    ctx: Optional[ConversationContext],
    memory_context: str,
) -> str:
    """Build the user-facing prompt with context injection."""
    parts = []

    if memory_context:
        parts.append(f"[User preferences]\n{memory_context}\n")

    if ctx and ctx.has_music_context():
        parts.append(f"[Current music context]\n{ctx.get_music_summary()}\n")

    if ctx and ctx.messages:
        history = ctx.get_history_for_llm()
        if history:
            history_text = "\n".join(
                f"{m['role'].upper()}: {m['content']}" for m in history[-4:]
            )
            parts.append(f"[Recent conversation]\n{history_text}\n")

    parts.append(f"[User message]\n{message}")
    return "\n".join(parts)


def _parse_llm_response(data: Dict[str, Any]) -> IntentResult:
    """Parse dict into IntentResult."""
    return IntentResult(
        intent=data.get("intent", "general_conversation"),
        confidence=float(data.get("confidence", 0.7)),
        requires_tool=bool(data.get("requires_tool", False)),
        tool=data.get("tool"),
        arguments=data.get("arguments") or {},
        needs_clarification=bool(data.get("needs_clarification", False)),
        clarification_question=data.get("clarification_question"),
        response_hint=data.get("response_hint"),
        steps=data.get("steps") or [],
    )


def _fallback_intent() -> IntentResult:
    """Return a safe fallback when LLM analysis fails."""
    return IntentResult(
        intent="general_conversation",
        confidence=0.5,
        requires_tool=False,
        response_hint="I'm not sure I understood that. Could you rephrase?",
    )


class IntentAnalyzer:
    """
    Analyzes user messages and returns structured IntentResult.

    Pipeline:
        1. Fast context-aware pre-check (no LLM)
        2. llm_service call with structured JSON output
        3. Fallback on any error
    """

    async def analyze(
        self,
        message: str,
        ctx: Optional[ConversationContext] = None,
        memory_context: str = "",
    ) -> IntentResult:
        """
        Analyze a user message and return an IntentResult.
        """
        logger.info(f"[AI-BRAIN] Input: {message!r}")

        # ── Step 1: fast context-aware pre-check ────────────────────────────
        fast = _fast_context_check(message, ctx)
        if fast is not None:
            logger.info(f"[AI-BRAIN] Fast-path intent: {fast.intent}")
            return fast

        # ── Step 2: LLM analysis ────────────────────────────────────────────
        if not llm_service.is_configured():
            logger.warning("[AI-BRAIN] No LLM API key configured — using rule-based fallback.")
            return self._no_llm_fallback(message, ctx)

        user_prompt = _build_user_prompt(message, ctx, memory_context)

        try:
            json_data = await llm_service.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1,
            )

            if not json_data:
                logger.warning("[AI-BRAIN] LLM returned empty JSON — fallback.")
                return _fallback_intent()

            result = _parse_llm_response(json_data)
            logger.info(f"[AI-BRAIN] LLM Intent: {result.intent} (conf={result.confidence:.2f})")
            return result

        except Exception as exc:
            logger.error(f"[AI-BRAIN] LLM analysis error: {exc}", exc_info=True)
            return _fallback_intent()

    def _no_llm_fallback(
        self,
        message: str,
        ctx: Optional[ConversationContext],
    ) -> IntentResult:
        """
        Rule-based fallback used when no LLM API key is available.
        Handles common natural language patterns without AI.
        """
        norm = message.lower().strip()

        # What's playing?
        if any(kw in norm for kw in ["what's playing", "what is playing", "current song", "now playing"]):
            return IntentResult(
                intent="music_current_track",
                confidence=0.9,
                requires_tool=True,
                tool="music_current_track",
            )

        # Open in Spotify
        open_match = re.search(r"open\s+(.+?)(?:\s+(?:on|in)\s+spotify)?$", norm)
        if open_match:
            q = open_match.group(1).strip()
            return IntentResult(
                intent="open_spotify",
                confidence=0.9,
                requires_tool=True,
                tool="open_spotify",
                arguments={"query": q},
                response_hint=f"Opening {q} in Spotify.",
            )

        # Artist search: "find songs by X", "songs by X", "tracks by X"
        artist_match = re.search(r"(?:find\s+(?:songs|tracks|music)\s+by|songs\s+by)\s+(.+)", norm)
        if artist_match:
            artist_q = artist_match.group(1).strip()
            return IntentResult(
                intent="artist_search",
                confidence=0.9,
                requires_tool=True,
                tool="artist_search",
                arguments={"artist": artist_q, "query": artist_q},
                response_hint=f"Here are songs by {artist_q}.",
            )

        # Play requests (YouTube provider default)
        play_match = re.search(r"(?:play|listen\s+to|put\s+on)\s+(.+)", norm)
        if play_match:
            raw_q = play_match.group(1).strip()
            if re.search(r"\b(?:on|in)\s+spotify\b", raw_q):
                clean_sp = re.sub(r"\b(?:on|in)\s+spotify\b", "", raw_q).strip()
                return IntentResult(
                    intent="open_spotify",
                    confidence=0.92,
                    requires_tool=True,
                    tool="open_spotify",
                    arguments={"query": clean_sp, "track": clean_sp, "provider": "spotify"},
                    response_hint=f"Opening {clean_sp} in Spotify.",
                )

            clean_yt = re.sub(r"\b(?:on|in)\s+youtube\b", "", raw_q).strip()
            by_match = re.search(r"(.+?)\s+by\s+(.+)", clean_yt)
            track_name = by_match.group(1).strip() if by_match else clean_yt
            artist_name = by_match.group(2).strip() if by_match else None
            return IntentResult(
                intent="music_play",
                confidence=0.92,
                requires_tool=True,
                tool="music_play",
                arguments={
                    "query": clean_yt,
                    "track": track_name,
                    "artist": artist_name,
                    "provider": "youtube",
                },
                response_hint=f"Playing {clean_yt} from YouTube.",
            )

        # Search requests (Spotify provider default)
        search_match = re.search(r"(?:search(?:\s+for)?|find|look\s+up)\s+(.+)", norm)
        if search_match:
            query = search_match.group(1).strip()
            by_match = re.search(r"(.+?)\s+by\s+(.+)", query)
            track_name = by_match.group(1).strip() if by_match else query
            artist_name = by_match.group(2).strip() if by_match else None
            lang = "Tamil" if "tamil" in query else ("Hindi" if "hindi" in query else None)

            return IntentResult(
                intent="music_search",
                confidence=0.88,
                requires_tool=True,
                tool="music_search",
                arguments={
                    "query": query,
                    "track": track_name,
                    "artist": artist_name,
                    "language": lang,
                    "version_preference": "original",
                    "action": "search",
                    "provider": "spotify",
                },
                response_hint=f"Searching for {query}.",
            )

        # Capabilities
        if any(kw in norm for kw in ["what can you", "capabilities", "what do you do", "help"]):
            return IntentResult(
                intent="assistant_capabilities",
                confidence=0.9,
                requires_tool=False,
                response_hint="I can discover music, search tracks on Spotify, and chat with you!",
            )

        # Fallback: treat as general conversation
        return IntentResult(
            intent="general_conversation",
            confidence=0.6,
            requires_tool=False,
            response_hint=(
                "I can help you search and find music on Spotify! Try saying 'Find Pattuma' or 'Search songs by A R Rahman'."
            ),
        )


# Singleton instance
intent_analyzer = IntentAnalyzer()
