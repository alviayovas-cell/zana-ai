"""
soundcloud_ranker.py — Deterministic SoundCloud search result ranking engine for Zana.

Ranks candidates using:
  + exact title match
  + artist/creator match (metadata_artist or user.username)
  + phrase similarity
  + requested artist match
  + playable access state ("playable" vs "preview" vs "blocked")
  + stream availability

Penalizes obvious mismatches unless explicitly requested:
  - remix
  - cover
  - karaoke
  - instrumental
  - live
  - unrelated / fan upload
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
    "parody": re.compile(r"\b(parody|spoof)\b", re.IGNORECASE),
}

OFFICIAL_CREATOR_SIGNALS = re.compile(
    r"(?:official|records|recordings|music|vevo|label|entertainment)\b",
    re.IGNORECASE,
)


@dataclass
class ScoredSoundCloudTrack:
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
    """Strip command prefixes and provider mentions to isolate the target track name."""
    norm = _normalize(query)
    norm = re.sub(r"^(?:please\s+)?(?:play|listen to|put on|find|search for|search|show me|open|get)\s+", "", norm)
    norm = re.sub(r"\s+(?:on|in|from)\s+(?:soundcloud|spotify|youtube)$", "", norm)
    norm = re.sub(r"\s+(?:song|track|audio|music)$", "", norm)
    norm_title_only = re.sub(r"\s+by\s+.+$", "", norm)
    return norm_title_only.strip() or norm.strip()


class SoundCloudRanker:
    """Deterministic result ranker for SoundCloud tracks."""

    def rank_tracks(
        self,
        items: List[Dict[str, Any]],
        query: str,
        artist_hint: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Ranks SoundCloud track dictionaries deterministically.
        Returns a sorted list ordered by highest score first.
        """
        if not items:
            return []

        norm_query = _normalize(query)
        clean_title_target = _clean_query(query)
        norm_artist = _normalize(artist_hint) if artist_hint else ""

        # Check if the user specifically asked for an artist via "by <artist>"
        if not norm_artist:
            by_match = re.search(r"\bby\s+(.+)$", norm_query)
            if by_match:
                norm_artist = _normalize(by_match.group(1))

        # Check if user explicitly asked for a variant
        user_wants_remix = bool(PENALTY_PATTERNS["remix"].search(norm_query))
        user_wants_cover = bool(PENALTY_PATTERNS["cover"].search(norm_query))
        user_wants_karaoke = bool(PENALTY_PATTERNS["karaoke"].search(norm_query))
        user_wants_instrumental = bool(PENALTY_PATTERNS["instrumental"].search(norm_query))
        user_wants_live = bool(PENALTY_PATTERNS["live"].search(norm_query))
        user_wants_lofi = bool(PENALTY_PATTERNS["lofi"].search(norm_query))

        target_tokens = set(clean_title_target.split())
        scored: List[ScoredSoundCloudTrack] = []

        for idx, item in enumerate(items):
            score = 100.0  # Base score
            reasons: List[str] = []
            is_official = False

            title = item.get("title", "") or item.get("name", "")
            norm_title = _normalize(title)

            # Artist / creator info
            creator_name = ""
            user_obj = item.get("user")
            if isinstance(user_obj, dict):
                creator_name = user_obj.get("username", "") or user_obj.get("name", "")
            metadata_artist = item.get("metadata_artist") or item.get("artist") or creator_name or ""
            norm_creator = _normalize(creator_name)
            norm_metadata_artist = _normalize(metadata_artist)

            # 1. Playable Access Verification (Critical Acceptance Requirement)
            access = (item.get("access") or "playable").lower()
            streamable = item.get("streamable", True)

            if access == "playable" and streamable:
                score += 30.0
                reasons.append("playable_track_bonus")
            elif access == "preview":
                score -= 20.0
                reasons.append("preview_only_penalty")
            elif access == "blocked" or not streamable:
                score -= 100.0
                reasons.append("blocked_stream_penalty")

            # 2. Exact Title Match Bonus
            if norm_title == clean_title_target:
                score += 50.0
                reasons.append("exact_title_match")
            elif clean_title_target and clean_title_target in norm_title:
                score += 30.0
                reasons.append("title_contains_query")

            # 3. Target token coverage
            if target_tokens:
                title_tokens = set(norm_title.split())
                matched_tokens = target_tokens.intersection(title_tokens)
                coverage = len(matched_tokens) / len(target_tokens)
                if coverage == 1.0:
                    score += 25.0
                    reasons.append("all_title_tokens_matched")
                elif coverage > 0.5:
                    score += 15.0 * coverage
                    reasons.append(f"partial_token_match_{int(coverage*100)}pct")

            # 4. Artist / Creator Match Bonus
            if norm_artist:
                if (norm_artist == norm_metadata_artist) or (norm_artist == norm_creator):
                    score += 55.0
                    reasons.append(f"exact_artist_match_{norm_artist}")
                elif norm_artist in norm_metadata_artist or norm_artist in norm_creator:
                    score += 35.0
                    reasons.append(f"partial_artist_match_{norm_artist}")
                elif norm_artist in norm_title:
                    score += 25.0
                    reasons.append(f"artist_in_title_{norm_artist}")
                else:
                    # Requested artist not found in title, creator, or metadata
                    score -= 30.0
                    reasons.append("requested_artist_mismatch")

            # 5. Official signals
            if OFFICIAL_CREATOR_SIGNALS.search(norm_creator) or OFFICIAL_CREATOR_SIGNALS.search(norm_metadata_artist):
                score += 15.0
                is_official = True
                reasons.append("verified_creator_signal")

            # 6. Apply Penalties for unwanted variants
            for p_name, pattern in PENALTY_PATTERNS.items():
                wants_variant = (
                    (p_name == "remix" and user_wants_remix)
                    or (p_name == "cover" and user_wants_cover)
                    or (p_name == "karaoke" and user_wants_karaoke)
                    or (p_name == "instrumental" and user_wants_instrumental)
                    or (p_name == "live" and user_wants_live)
                    or (p_name == "lofi" and user_wants_lofi)
                )
                if not wants_variant and pattern.search(norm_title):
                    score -= 40.0
                    reasons.append(f"penalized_{p_name}")

            # Position bias: slightly prefer earlier search results as tie-breaker
            score -= idx * 0.5

            scored.append(
                ScoredSoundCloudTrack(
                    item=item,
                    score=round(score, 2),
                    reasons=reasons,
                    is_official=is_official,
                )
            )

        # Sort descending by score
        scored.sort(key=lambda x: x.score, reverse=True)

        ranked_items: List[Dict[str, Any]] = []
        for s in scored:
            it = dict(s.item)
            it["ranking_score"] = s.score
            it["_ranking_score"] = s.score
            it["ranking_reasons"] = s.reasons
            it["_ranking_reasons"] = s.reasons
            it["is_official"] = s.is_official
            it["_is_official"] = s.is_official
            ranked_items.append(it)

        return ranked_items


# Global singleton instance
soundcloud_ranker = SoundCloudRanker()
