import time
from typing import Optional, Dict, Any, List

import httpx

from app.core.logging_config import logger


AUDIUS_APP_NAME = "Zana"
AUDIUS_BOOTSTRAP = "https://api.audius.co"


class FreeMusicService:
    """
    100% Free Music Streaming & Search Service using the Audius public API.

    Audius is a decentralised, free music platform. Its REST API needs no
    API key and its stream endpoints serve full-length tracks with permissive
    CORS headers, so audio can be played directly in the browser from any
    server IP (unlike YouTube/yt-dlp, which blocks datacentre IPs).
    """

    def __init__(self) -> None:
        self._host: Optional[str] = None
        self._host_fetched_at: float = 0.0
        self._host_ttl: float = 1800.0  # refresh discovery host every 30 min

    def _get_host(self) -> Optional[str]:
        """Return a healthy Audius discovery node, cached for a while."""
        now = time.time()
        if self._host and (now - self._host_fetched_at) < self._host_ttl:
            return self._host
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(AUDIUS_BOOTSTRAP)
                resp.raise_for_status()
                hosts: List[str] = resp.json().get("data", [])
            if hosts:
                self._host = hosts[0]
                self._host_fetched_at = now
                logger.info(f"[AUDIUS] Using discovery node: {self._host}")
                return self._host
            logger.error("[AUDIUS] Bootstrap returned no discovery nodes.")
        except Exception as exc:
            logger.error(f"[AUDIUS] Failed to fetch discovery nodes: {exc}")
        return None

    def search_and_extract(self, query: str) -> Optional[Dict[str, Any]]:
        """Search Audius for a track and return its direct streaming audio URL."""
        host = self._get_host()
        if not host:
            return None

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    f"{host}/v1/tracks/search",
                    params={"query": query, "app_name": AUDIUS_APP_NAME},
                )
            if resp.status_code != 200:
                logger.error(f"[AUDIUS] Search error {resp.status_code}: {resp.text[:200]}")
                return None

            tracks: List[Dict[str, Any]] = resp.json().get("data", []) or []
            # Keep only tracks we can actually stream for free
            playable = [
                t for t in tracks
                if t.get("id")
                and not t.get("is_delete")
                and not t.get("is_stream_gated")
                and t.get("is_streamable", True)
            ]
            if not playable:
                logger.info(f"[AUDIUS] No streamable track for '{query}'")
                return None

            track = playable[0]
            track_id = track["id"]
            stream_url = f"{host}/v1/tracks/{track_id}/stream?app_name={AUDIUS_APP_NAME}"

            artwork = track.get("artwork") or {}
            album_art = (
                artwork.get("480x480")
                or artwork.get("150x150")
                or artwork.get("1000x1000")
                or None
            )
            user = track.get("user") or {}
            permalink = track.get("permalink") or ""

            return {
                "id": str(track_id),
                "title": track.get("title") or query,
                "artist": user.get("name") or user.get("handle") or "Unknown Artist",
                "album_art": album_art,
                "audio_url": stream_url,
                "duration": int(track.get("duration") or 0),
                "webpage_url": f"https://audius.co{permalink}" if permalink else None,
            }
        except Exception as exc:
            logger.error(f"[AUDIUS] search_and_extract error for '{query}': {exc}")
            return None


free_music_service = FreeMusicService()
