"""
music_ranker.py — Deterministic Spotify search result ranking engine.

Implements explainable, weighted ranking so Zana avoids blindly selecting results[0].
Prioritizes official tracks, exact title/artist matches, and language relevance while
penalizing covers, remixes, karaoke, instrumental, and fan tributes unless explicitly requested.
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
    "lofi": re.compile(r"\b(lo-?fi|chill mix|slowed(\s+and\s+|\s*\+\s*)reverb)\b", re.IGNORECASE),
    "tribute": re.compile(r"\b(tribute|homage|in the style of)\b", re.IGNORECASE),
    "rerecorded": re.compile(r"\b(re-?recorded|new version)\b", re.IGNORECASE),
}


@dataclass
class ScoredTrack:
    item: Dict[str, Any]
    score: float
    reasons: List[str] = field(default_factory=list)


def _normalize(text: str) -> str:
    """Lowercase and strip punctuation/symbols for normalized matching."""
    if not text:
        return ""
    text = text.lower()
    # Replace common punctuation with space
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def _clean_query(query: str) -> str:
    """Strip command prefixes like 'play', 'find', 'search' to isolate the target track name."""
    norm = _normalize(query)
    # Strip common command prefixes
    norm = re.sub(r"^(?:please\s+)?(?:play|listen to|put on|find|search for|search|show me|open|get)\s+", "", norm)
    # Strip trailing filler like 'song', 'track', 'music' if at end
    norm = re.sub(r"\s+(?:song|track|music)$", "", norm)
    # Strip artist clauses like 'by imagine dragons' when comparing pure title
    norm_title_only = re.sub(r"\s+by\s+.+$", "", norm)
    return norm_title_only.strip() or norm.strip()


class MusicRanker:
    """Deterministic result ranker for Spotify tracks."""

    def rank_tracks(
        self,
        items: List[Dict[str, Any]],
        query: str,
        artist_hint: Optional[str] = None,
        language_hint: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Ranks Spotify track dictionaries in-place or returns a sorted list.
        Each item is evaluated and ordered by highest score first.
        """
        if not items:
            return []

        scored: List[ScoredTrack] = []
        norm_query = _normalize(query)
        clean_title_target = _clean_query(query)
        norm_artist = _normalize(artist_hint) if artist_hint else ""

        # Check if the user explicitly searched for a variant
        user_wants_remix = bool(re.search(r"\bremix\b", norm_query))
        user_wants_cover = bool(re.search(r"\bcover\b", norm_query))
        user_wants_karaoke = bool(re.search(r"\bkaraoke\b", norm_query))
        user_wants_instrumental = bool(re.search(r"\binstrumental\b", norm_query))
        user_wants_live = bool(re.search(r"\blive\b", norm_query))
        user_wants_lofi = bool(re.search(r"\blo-?fi\b", norm_query))

        target_tokens = set(clean_title_target.split())

        for idx, item in enumerate(items):
            score = 100.0  # Base score
            reasons: List[str] = []

            title = item.get("name", "")
            norm_title = _normalize(title)

            # Extract artists list
            artists = item.get("artists", [])
            artist_names = [a.get("name", "") for a in artists if isinstance(a, dict)]
            norm_artists = [_normalize(name) for name in artist_names]

            album = item.get("album", {})
            album_name = album.get("name", "") if isinstance(album, dict) else ""
            norm_album = _normalize(album_name)
            album_type = album.get("album_type", "") if isinstance(album, dict) else ""

            # 1. Exact / Substring Title Match
            if norm_title == clean_title_target or norm_title == norm_query:
                score += 120.0
                reasons.append("exact_title_match (+120)")
            elif clean_title_target and (clean_title_target in norm_title or norm_title in clean_title_target):
                score += 60.0
                reasons.append("substring_title_match (+60)")
            else:
                # Token overlap in title
                title_tokens = set(norm_title.split())
                overlap = target_tokens.intersection(title_tokens)
                if overlap:
                    token_score = len(overlap) * 15.0
                    score += token_score
                    reasons.append(f"token_overlap (+{token_score})")

            # 2. Artist Match
            if norm_artist:
                matched_artist = any(norm_artist in a or a in norm_artist for a in norm_artists)
                if matched_artist:
                    score += 100.0
                    reasons.append("explicit_artist_match (+100)")
                else:
                    score -= 30.0
                    reasons.append("artist_mismatch (-30)")
            else:
                # Check if query contained the artist name
                for a_name, norm_a in zip(artist_names, norm_artists):
                    if norm_a and norm_a in norm_query:
                        score += 80.0
                        reasons.append(f"query_contains_artist:{a_name} (+80)")
                        break

            # 3. Official Release / Album signals
            if album_type in ("album", "single"):
                score += 20.0
                reasons.append(f"album_type_{album_type} (+20)")
            elif album_type == "compilation":
                score -= 10.0
                reasons.append("compilation_album (-10)")

            # Popularity signal (Spotify returns popularity 0-100)
            popularity = item.get("popularity", 0) or 0
            pop_score = (popularity / 100.0) * 30.0
            score += pop_score
            reasons.append(f"popularity_{popularity} (+{pop_score:.1f})")

            # Playability signal
            is_playable = item.get("is_playable")
            if is_playable is False:
                score -= 60.0
                reasons.append("unplayable_track (-60)")

            # 4. Variant matching & penalties
            full_track_text = f"{norm_title} {norm_album}"

            if user_wants_remix:
                if PENALTY_PATTERNS["remix"].search(full_track_text):
                    score += 80.0
                    reasons.append("requested_remix_boost (+80)")
            else:
                if PENALTY_PATTERNS["remix"].search(full_track_text):
                    score -= 45.0
                    reasons.append("unwanted_remix (-45)")

            if user_wants_cover:
                if PENALTY_PATTERNS["cover"].search(full_track_text):
                    score += 80.0
                    reasons.append("requested_cover_boost (+80)")
            else:
                if PENALTY_PATTERNS["cover"].search(full_track_text):
                    score -= 55.0
                    reasons.append("unwanted_cover (-55)")

            if not user_wants_karaoke and PENALTY_PATTERNS["karaoke"].search(full_track_text):
                score -= 75.0
                reasons.append("unwanted_karaoke (-75)")

            if not user_wants_instrumental and PENALTY_PATTERNS["instrumental"].search(full_track_text):
                score -= 50.0
                reasons.append("unwanted_instrumental (-50)")

            if not user_wants_live and PENALTY_PATTERNS["live"].search(full_track_text):
                score -= 35.0
                reasons.append("unwanted_live (-35)")

            if not user_wants_lofi and PENALTY_PATTERNS["lofi"].search(full_track_text):
                score -= 40.0
                reasons.append("unwanted_lofi (-40)")

            if PENALTY_PATTERNS["tribute"].search(full_track_text):
                score -= 60.0
                reasons.append("tribute_variant (-60)")

            if PENALTY_PATTERNS["rerecorded"].search(full_track_text):
                score -= 30.0
                reasons.append("rerecorded_variant (-30)")

            # 5. Language / Regional Hint
            if language_hint:
                lang = language_hint.lower()
                # Check title, album, artists for language match
                if lang in norm_query or lang in norm_album or lang in norm_title:
                    score += 25.0
                    reasons.append(f"language_hint_{lang} (+25)")

            # Original position tie-breaker (give minor preference to earlier Spotify results)
            position_bias = max(0.0, 10.0 - idx)
            score += position_bias

            scored.append(ScoredTrack(item=item, score=score, reasons=reasons))

        # Sort descending by score
        scored.sort(key=lambda x: x.score, reverse=True)

        # Attach explainability metadata to items for debugging/inspection
        ranked_items = []
        for st in scored:
            it = dict(st.item)
            it["_ranking_score"] = round(st.score, 2)
            it["_ranking_reasons"] = st.reasons
            ranked_items.append(it)

        return ranked_items


music_ranker = MusicRanker()
