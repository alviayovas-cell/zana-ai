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
