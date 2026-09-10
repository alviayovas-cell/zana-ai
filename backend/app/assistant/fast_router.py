"""
fast_router.py — High-performance Fast Command Router for Zana (Phase 5).

Provides instant (<5ms) deterministic intent classification for unambiguous commands:
  - MUSIC_PAUSE         ("pause", "stop playback", "pause song")
  - MUSIC_RESUME        ("resume", "unpause", "continue music")
  - MUSIC_NEXT          ("next song", "skip song", "next track")
  - MUSIC_PREVIOUS      ("previous song", "go back", "last song")
  - MUSIC_VOLUME        ("volume 50", "set volume to 80")
  - MUSIC_CURRENT_TRACK ("what is playing?", "what's playing?", "current song")
  - GREETING, HELP, STATUS

Safety:
  If a request is ambiguous or complex (e.g. "next one" without playing music, or
  "play something relaxing"), fast_router returns matched=False with confidence < 0.95,
  passing execution directly to the AI Brain.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.assistant.commands import CommandAction, ParsedCommand
from app.core.logging_config import logger


@dataclass
class FastRouteResult:
    """Result returned by the Fast Command Router."""

    matched: bool
    action: CommandAction = CommandAction.UNKNOWN
    query: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    reason: str = ""

    def to_parsed_command(self) -> ParsedCommand:
        return ParsedCommand(
            action=self.action,
            query=self.query,
            parameters=self.parameters,
            confidence=self.confidence,
        )


class FastCommandRouter:
    """
    Evaluates incoming user text messages using high-confidence regex rules.
    Bypasses LLM for clear deterministic commands.
    """

    # Unambiguous exact / boundary regex patterns
    _PAUSE_RE = re.compile(
        r"^(?:please\s+)?(?:pause|stop music|pause song|stop playback|pause playback|pause music|stop the music|stop)\s*$",
        re.IGNORECASE,
    )
    _RESUME_RE = re.compile(
        r"^(?:please\s+)?(?:resume|unpause|continue playing|continue music|play again|resume music|resume playing)\s*$",
        re.IGNORECASE,
    )
    _NEXT_RE = re.compile(
        r"^(?:please\s+)?(?:next|skip|next\s+song|skip\s+song|next\s+track|skip\s+track|play\s+next)\s*$",
        re.IGNORECASE,
    )
    _PREV_RE = re.compile(
        r"^(?:please\s+)?(?:prev|previous|previous\s+song|last\s+song|go\s+back|previous\s+track|replay\s+song)\s*$",
        re.IGNORECASE,
    )
    _VOL_RE = re.compile(
        r"^(?:please\s+)?(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})%?\s*$",
        re.IGNORECASE,
    )
    _VOL_SHORT_RE = re.compile(
        r"^vol(?:ume)?\s+(\d{1,3})%?\s*$",
        re.IGNORECASE,
    )
    _WHAT_PLAYING_RE = re.compile(
        r"^(?:what'?s?\s+(?:is\s+)?(?:playing|on)|what\s+song\s+is\s+this|which\s+song\s+is\s+this|current\s+track|current\s+song)\s*$",
        re.IGNORECASE,
    )
    _GREETING_RE = re.compile(
        r"^(hi|hello|hey|greetings|hola|namaste|good\s+morning|good\s+evening)\b",
        re.IGNORECASE,
    )
    _HELP_RE = re.compile(
        r"^(help|what\s+can\s+you\s+do|commands|features|list\s+commands)\s*$",
        re.IGNORECASE,
    )
    _STATUS_RE = re.compile(
        r"^(status|system\s+status|ping|are\s+you\s+online)\s*$",
        re.IGNORECASE,
    )
    # Music Discovery & Provider-Aware Launcher Patterns
    _OPEN_SPOTIFY_RE = re.compile(
        r"^(?:please\s+)?(?:open|play)\s+(.+?)\s+(?:on|in)\s+spotify\s*$",
        re.IGNORECASE,
    )
    _OPEN_SPOTIFY_BARE_RE = re.compile(
        r"^(?:please\s+)?open\s+(.+?)(?:\s+(?:on|in)\s+spotify)?\s*$",
        re.IGNORECASE,
    )
    _PLAY_YOUTUBE_EXPLICIT_RE = re.compile(
        r"^(?:please\s+)?(?:play(?:\s+(?:this|it|song|track))?\s+(?:on|in)\s+youtube|watch\s+(?:on|in)\s+youtube)(?:\s+(.+))?\s*$",
        re.IGNORECASE,
    )
    _FIND_ARTIST_RE = re.compile(
        r"^(?:please\s+)?(?:find\s+(?:songs|tracks|music)\s+by|search\s+artist|songs\s+by)\s+(.+?)\s*$",
        re.IGNORECASE,
    )
    _SEARCH_RE = re.compile(
        r"^(?:please\s+)?(?:find|search(?:\s+for)?|look\s+up)\s+(.+?)\s*$",
        re.IGNORECASE,
    )
    _PLAY_RE = re.compile(
        r"^(?:please\s+)?(?:play|listen\s+to|put\s+on)\s+(.+?)\s*$",
        re.IGNORECASE,
    )

    def route(self, text: str) -> FastRouteResult:
        """
        Evaluate text input.
        Returns FastRouteResult with matched=True if intent is recognized with confidence >= 0.95.
        """
        norm = text.strip()
        if not norm:
            return FastRouteResult(matched=False, reason="Empty text")

        # 1. Pause
        if self._PAUSE_RE.match(norm):
            logger.info(f"[ROUTER] Input: {norm!r} | Matched: MUSIC_PAUSE | Confidence: 0.99 | Mode: FastDirect")
            return FastRouteResult(
                matched=True,
                action=CommandAction.MUSIC_PAUSE,
                query=norm,
                confidence=0.99,
                reason="Exact pause match",
            )

        # 2. Resume
        if self._RESUME_RE.match(norm):
            logger.info(f"[ROUTER] Input: {norm!r} | Matched: MUSIC_RESUME | Confidence: 0.99 | Mode: FastDirect")
            return FastRouteResult(
                matched=True,
                action=CommandAction.MUSIC_RESUME,
                query=norm,
                confidence=0.99,
                reason="Exact resume match",
            )

        # 3. Next
        if self._NEXT_RE.match(norm):
            logger.info(f"[ROUTER] Input: {norm!r} | Matched: MUSIC_NEXT | Confidence: 0.99 | Mode: FastDirect")
            return FastRouteResult(
                matched=True,
                action=CommandAction.MUSIC_NEXT,
                query=norm,
                confidence=0.99,
                reason="Exact next match",
            )

        # 4. Previous
        if self._PREV_RE.match(norm):
            logger.info(f"[ROUTER] Input: {norm!r} | Matched: MUSIC_PREVIOUS | Confidence: 0.99 | Mode: FastDirect")
            return FastRouteResult(
                matched=True,
                action=CommandAction.MUSIC_PREVIOUS,
                query=norm,
                confidence=0.99,
                reason="Exact previous match",
            )

        # 5. Volume
        vol_match = self._VOL_RE.match(norm) or self._VOL_SHORT_RE.match(norm)
        if vol_match:
            try:
                vol_val = int(vol_match.group(1))
                clamped = max(0, min(100, vol_val))
                logger.info(f"[ROUTER] Input: {norm!r} | Matched: MUSIC_VOLUME ({clamped}%) | Confidence: 0.99 | Mode: FastDirect")
                return FastRouteResult(
                    matched=True,
                    action=CommandAction.MUSIC_VOLUME,
                    query=norm,
                    parameters={"volume": clamped},
                    confidence=0.99,
                    reason=f"Volume set to {clamped}%",
                )
            except (ValueError, IndexError):
                pass

        # 6. What's playing?
        if self._WHAT_PLAYING_RE.match(norm):
            logger.info(f"[ROUTER] Input: {norm!r} | Matched: MUSIC_CURRENT_TRACK | Confidence: 0.98 | Mode: FastDirect")
            return FastRouteResult(
                matched=True,
                action=CommandAction.MUSIC_CURRENT_TRACK,
                query=norm,
                confidence=0.98,
                reason="Current track query match",
            )

        # 7. Greeting
        if self._GREETING_RE.match(norm):
            logger.info(f"[ROUTER] Input: {norm!r} | Matched: GREETING | Confidence: 0.99 | Mode: FastDirect")
            return FastRouteResult(
                matched=True,
                action=CommandAction.GREETING,
                query=norm,
                confidence=0.99,
                reason="Greeting match",
            )

        # 8. Help
        if self._HELP_RE.match(norm):
            logger.info(f"[ROUTER] Input: {norm!r} | Matched: HELP | Confidence: 0.99 | Mode: FastDirect")
            return FastRouteResult(
                matched=True,
                action=CommandAction.HELP,
                query=norm,
                confidence=0.99,
                reason="Help match",
            )

        # 9. Status
        if self._STATUS_RE.match(norm):
            logger.info(f"[ROUTER] Input: {norm!r} | Matched: STATUS | Confidence: 0.99 | Mode: FastDirect")
            return FastRouteResult(
                matched=True,
                action=CommandAction.STATUS,
                query=norm,
                confidence=0.99,
                reason="Status match",
            )

        # 10. Explicit Play on YouTube
        yt_explicit_match = self._PLAY_YOUTUBE_EXPLICIT_RE.match(norm)
        if yt_explicit_match:
            yt_q = (yt_explicit_match.group(1) or "").strip()
            params = {"provider": "youtube"}
            if yt_q:
                params["query"] = yt_q
                by_match = re.search(r"(.+?)\s+by\s+(.+)", yt_q, re.IGNORECASE)
                if by_match:
                    params["track"] = by_match.group(1).strip()
                    params["artist"] = by_match.group(2).strip()
                else:
                    params["track"] = yt_q
            logger.info(f"[ROUTER] Input: {norm!r} | Matched: MUSIC_PLAY on YouTube ({yt_q!r}) | Confidence: 0.98 | Mode: FastDirect")
            return FastRouteResult(
                matched=True,
                action=CommandAction.MUSIC_PLAY,
                query=yt_q or norm,
                parameters=params,
                confidence=0.98,
                reason=f"Direct play on YouTube match: {yt_q or 'current/explicit'}",
            )

        # 11. Open in Spotify
        open_sp_match = self._OPEN_SPOTIFY_RE.match(norm) or self._OPEN_SPOTIFY_BARE_RE.match(norm)
        if open_sp_match:
            song_q = open_sp_match.group(1).strip()
            logger.info(f"[ROUTER] Input: {norm!r} | Matched: OPEN_SPOTIFY ({song_q!r}) | Confidence: 0.98 | Mode: FastDirect")
            return FastRouteResult(
                matched=True,
                action=CommandAction.OPEN_SPOTIFY,
                query=song_q,
                parameters={"query": song_q, "track": song_q, "provider": "spotify"},
                confidence=0.98,
                reason=f"Direct open Spotify match: {song_q}",
            )

        # 12. Find / Search Artist
        artist_match = self._FIND_ARTIST_RE.match(norm)
        if artist_match:
            artist_q = artist_match.group(1).strip()
            logger.info(f"[ROUTER] Input: {norm!r} | Matched: ARTIST_SEARCH ({artist_q!r}) | Confidence: 0.98 | Mode: FastDirect")
            return FastRouteResult(
                matched=True,
                action=CommandAction.ARTIST_SEARCH,
                query=artist_q,
                parameters={"artist": artist_q, "query": artist_q},
                confidence=0.98,
                reason=f"Artist search match: {artist_q}",
            )

        # 13. Search / Find Song or Topic
        search_match = self._SEARCH_RE.match(norm)
        if search_match:
            search_q = search_match.group(1).strip()
            # If query says "tamil songs by X", extract artist if present
            by_match = re.search(r"(.+?)\s+by\s+(.+)", search_q, re.IGNORECASE)
            params = {"query": search_q}
            if by_match:
                params["track"] = by_match.group(1).strip()
                params["artist"] = by_match.group(2).strip()
            logger.info(f"[ROUTER] Input: {norm!r} | Matched: MUSIC_SEARCH ({search_q!r}) | Confidence: 0.98 | Mode: FastDirect")
            return FastRouteResult(
                matched=True,
                action=CommandAction.MUSIC_SEARCH,
                query=search_q,
                parameters=params,
                confidence=0.98,
                reason=f"Music search match: {search_q}",
            )

        # 14. Play Song (YouTube provider default for in-page embedded playback)
        play_match = self._PLAY_RE.match(norm)
        if play_match:
            play_q = play_match.group(1).strip()
            # If query is ambiguous or mood-based (e.g. "play something relaxing"), delegate to AI Brain
            if re.search(r"\b(something|anything|some)\b", play_q, re.IGNORECASE):
                logger.info(f"[ROUTER] Input: {norm!r} | Ambiguous play query -> Delegating to AI Brain")
            else:
                # Check if user explicitly asked for Spotify in the play query
                if re.search(r"\b(?:on|in)\s+spotify\b", play_q, re.IGNORECASE):
                    clean_sp_q = re.sub(r"\b(?:on|in)\s+spotify\b", "", play_q, flags=re.IGNORECASE).strip()
                    logger.info(f"[ROUTER] Input: {norm!r} | Matched: OPEN_SPOTIFY via play ({clean_sp_q!r})")
                    return FastRouteResult(
                        matched=True,
                        action=CommandAction.OPEN_SPOTIFY,
                        query=clean_sp_q,
                        parameters={"query": clean_sp_q, "track": clean_sp_q, "provider": "spotify"},
                        confidence=0.98,
                        reason=f"Play on Spotify match: {clean_sp_q}",
                    )

                clean_play_q = re.sub(r"\b(?:on|in)\s+youtube\b", "", play_q, flags=re.IGNORECASE).strip()
                by_match = re.search(r"(.+?)\s+by\s+(.+)", clean_play_q, re.IGNORECASE)
                params = {"query": clean_play_q, "provider": "youtube"}
                if by_match:
                    params["track"] = by_match.group(1).strip()
                    params["artist"] = by_match.group(2).strip()
                else:
                    params["track"] = clean_play_q

                logger.info(f"[ROUTER] Input: {norm!r} | Matched: MUSIC_PLAY ({clean_play_q!r}) | Confidence: 0.98 | Mode: FastDirect")
                return FastRouteResult(
                    matched=True,
                    action=CommandAction.MUSIC_PLAY,
                    query=clean_play_q,
                    parameters=params,
                    confidence=0.98,
                    reason=f"Music play match: {clean_play_q}",
                )

        # Unmatched / Ambiguous / Complex -> Pass to AI Brain
        logger.info(f"[ROUTER] Input: {norm!r} | Not deterministic -> Delegating to AI Brain")
        return FastRouteResult(
            matched=False,
            action=CommandAction.UNKNOWN,
            query=norm,
            confidence=0.0,
            reason="Ambiguous/natural language query — delegating to AI Brain",
        )


# Singleton instance
fast_router = FastCommandRouter()
