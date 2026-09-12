"""
youtube_ranker.py — Deterministic YouTube search result ranking engine for Zana.

Ranks YouTube video results intelligently instead of blindly picking result[0].
Evaluates:
  - Exact title match and phrase similarity
  - Artist / Channel match
  - Official / recognized channel signals (VEVO, Topic, Official Artist channels)
  - Requested versions (original vs. remix vs. cover vs. lyrics)
  - Penalties for covers, remixes, karaoke, reaction videos, and fan uploads
  - Avoids claiming a result is "official" unless backed by metadata
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


PENALTY_PATTERNS = {
    "remix": re.compile(r"\b(remix|rmx|club mix|extended mix|vip mix)\b", re.IGNORECASE),
    "cover": re.compile(r"\b(cover|acoustic cover|originally performed by)\b", re.IGNORECASE),
    "karaoke": re.compile(r"\b(karaoke|backing track|instrumental version)\b", re.IGNORECASE),
    "instrumental": re.compile(r"\b(instrumental|minus one)\b", re.IGNORECASE),
    "live": re.compile(r"\b(live|live at|live from|in concert)\b", re.IGNORECASE),
    "lofi": re.compile(r"\b(lo-?fi|chill mix|slowed(\s+and\s+|\s*\+\s*)reverb|slowed down)\b", re.IGNORECASE),
    "tribute": re.compile(r"\b(tribute|homage|in the style of)\b", re.IGNORECASE),
    "lyrics": re.compile(r"\b(lyrics|lyric video|with lyrics|text video)\b", re.IGNORECASE),
    "junk": re.compile(r"\b(reaction|review|tutorial|how to play|lesson|guitar tab|bass boost|8d audio|1 hour|10 hours)\b", re.IGNORECASE),
    "shorts": re.compile(r"\b(shorts|#shorts|short video|status video|whatsapp status)\b", re.IGNORECASE),
}

OFFICIAL_SIGNALS_TITLE = re.compile(
    r"\b(?:official\s+(?:music\s+)?video|official\s+audio|official\s+lyric\s+video|official\s+visualizer|music\s+video)\b",
    re.IGNORECASE,
)

OFFICIAL_CHANNEL_SIGNALS = re.compile(
    r"(?:vevo|- topic|official|records|music|entertainment)\b",
    re.IGNORECASE,
)


@dataclass
class ScoredVideo:
    item: Dict[str, Any]
    score: float
    reasons: List[str] = field(default_factory=list)
    is_official: bool = False


def _normalize(text: str) -> str:
    """Lowercase and strip punctuation/symbols for normalized matching."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def _clean_query(query: str) -> str:
    """Strip command prefixes like 'play', 'find', 'search' and provider mentions."""
    norm = _normalize(query)
    norm = re.sub(r"^(?:please\s+)?(?:play|listen to|put on|find|search for|search|show me|open|get)\s+", "", norm)
    norm = re.sub(r"\s+(?:on|in|from)\s+(?:youtube|spotify|soundcloud)$", "", norm)
    norm = re.sub(r"\s+(?:song|track|music|video)$", "", norm)
    norm_title_only = re.sub(r"\s+by\s+.+$", "", norm)
    return norm_title_only.strip() or norm.strip()


class YouTubeRanker:
    """Deterministic result ranker for YouTube videos."""

    def rank_videos(
        self,
        items: List[Dict[str, Any]],
        query: str,
        artist_hint: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Ranks YouTube search items.
        Returns a sorted list ordered by highest score first.
        """
        if not items:
            return []

        norm_query = _normalize(query)
        clean_title_target = _clean_query(query)
        norm_artist = _normalize(artist_hint) if artist_hint else ""

        # Did user explicitly ask for specific variations?
        user_wants_remix = bool(PENALTY_PATTERNS["remix"].search(norm_query))
        user_wants_cover = bool(PENALTY_PATTERNS["cover"].search(norm_query))
        user_wants_karaoke = bool(PENALTY_PATTERNS["karaoke"].search(norm_query))
        user_wants_instrumental = bool(PENALTY_PATTERNS["instrumental"].search(norm_query))
        user_wants_live = bool(PENALTY_PATTERNS["live"].search(norm_query))
        user_wants_lofi = bool(PENALTY_PATTERNS["lofi"].search(norm_query))
        user_wants_lyrics = bool(PENALTY_PATTERNS["lyrics"].search(norm_query))

        target_tokens = set(clean_title_target.split())
        scored: List[ScoredVideo] = []

        for item in items:
            score = 100.0
            reasons: List[str] = []
            is_official = False

            title = item.get("title") or (item.get("snippet", {}).get("title", "") if isinstance(item.get("snippet"), dict) else "")
            channel = item.get("channelTitle") or item.get("channel_title") or (item.get("snippet", {}).get("channelTitle", "") if isinstance(item.get("snippet"), dict) else "")
            norm_title = _normalize(title)
            norm_channel = _normalize(channel)

            # 1. Exact or Substring Title Match
            if norm_title == clean_title_target or norm_title == norm_query:
                score += 120.0
                reasons.append("exact_title_match (+120)")
            elif clean_title_target and clean_title_target in norm_title:
                score += 65.0
                reasons.append("clean_title_in_result (+65)")
            elif norm_title and norm_title in clean_title_target:
                score += 45.0
                reasons.append("result_in_clean_title (+45)")
            else:
                title_tokens = set(norm_title.split())
                overlap = target_tokens.intersection(title_tokens)
                if overlap:
                    token_score = len(overlap) * 15.0
                    score += token_score
                    reasons.append(f"title_token_overlap (+{token_score})")

            # 2. Artist / Channel Match
            if norm_artist:
                if norm_artist in norm_channel or norm_channel in norm_artist:
                    score += 80.0
                    reasons.append(f"artist_channel_match '{artist_hint}' (+80)")
                elif norm_artist in norm_title:
                    score += 40.0
                    reasons.append(f"artist_in_title '{artist_hint}' (+40)")
            elif target_tokens:
                # Check if channel name matches any part of target query (e.g. artist inside query)
                channel_tokens = set(norm_channel.split())
                channel_overlap = target_tokens.intersection(channel_tokens)
                if channel_overlap:
                    score += 25.0
                    reasons.append("channel_query_overlap (+25)")

            # 3. Official / Recognized Channel Signals
            has_official_title = bool(OFFICIAL_SIGNALS_TITLE.search(title))
            has_official_channel = bool(OFFICIAL_CHANNEL_SIGNALS.search(channel))

            if has_official_title:
                score += 40.0
                reasons.append("official_title_signal (+40)")

            if has_official_channel:
                score += 35.0
                reasons.append("official_channel_signal (+35)")

            # Only mark is_official when metadata clearly supports it
            if has_official_channel or (has_official_title and (norm_artist in norm_channel or "vevo" in norm_channel)):
                is_official = True

            # 4. Penalties for Unwanted Variants
            if not user_wants_cover and PENALTY_PATTERNS["cover"].search(title):
                score -= 60.0
                reasons.append("cover_penalty (-60)")

            if not user_wants_remix and PENALTY_PATTERNS["remix"].search(title):
                score -= 60.0
                reasons.append("remix_penalty (-60)")

            if not user_wants_lyrics and PENALTY_PATTERNS["lyrics"].search(title):
                # Lyric videos are penalized if official video or audio exists
                score -= 40.0
                reasons.append("lyric_video_penalty (-40)")

            if not user_wants_karaoke and PENALTY_PATTERNS["karaoke"].search(title):
                score -= 50.0
                reasons.append("karaoke_penalty (-50)")

            if not user_wants_instrumental and PENALTY_PATTERNS["instrumental"].search(title):
                score -= 50.0
                reasons.append("instrumental_penalty (-50)")

            if not user_wants_live and PENALTY_PATTERNS["live"].search(title):
                score -= 30.0
                reasons.append("live_penalty (-30)")

            if not user_wants_lofi and PENALTY_PATTERNS["lofi"].search(title):
                score -= 35.0
                reasons.append("lofi_penalty (-35)")

            # Always penalize junk content (reactions, reviews, shorts)
            if PENALTY_PATTERNS["junk"].search(title):
                score -= 80.0
                reasons.append("junk_content_penalty (-80)")

            if PENALTY_PATTERNS["shorts"].search(title):
                score -= 70.0
                reasons.append("shorts_penalty (-70)")

            scored.append(ScoredVideo(item=item, score=score, reasons=reasons, is_official=is_official))

        # Sort descending by score
        scored.sort(key=lambda x: x.score, reverse=True)

        ranked_results = []
        for s in scored:
            enhanced = dict(s.item)
            if "videoId" not in enhanced:
                if isinstance(enhanced.get("id"), dict) and "videoId" in enhanced["id"]:
                    enhanced["videoId"] = enhanced["id"]["videoId"]
                elif isinstance(enhanced.get("id"), str):
                    enhanced["videoId"] = enhanced["id"]
            enhanced["ranking_score"] = round(s.score, 2)
            enhanced["ranking_reasons"] = s.reasons
            enhanced["is_official"] = s.is_official
            ranked_results.append(enhanced)

        return ranked_results


# Singleton instance
youtube_ranker = YouTubeRanker()
