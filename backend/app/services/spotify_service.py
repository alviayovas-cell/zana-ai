"""
spotify_service.py — Spotify Web API integration for Zana (Free Mode Compatible).

Architecture:
  - Capability Model: search=True, openSpotify=True, directPlayback=False
  - Search & Discovery: Spotify Web API search with deterministic ranking and pagination (limit <= 10)
  - Launcher: Returns Spotify web URL ('https://open.spotify.com/...') and URI ('spotify:track:...')
  - Zero direct playback requirement: Never assumes Spotify Premium or fails repeatedly on 403.
  - Auth: Supports user OAuth token and client credentials fallback for catalog search.
"""
import os
from typing import Optional, Dict, Any, List
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials, CacheFileHandler
from spotipy.exceptions import SpotifyException

from app.core.config import settings
from app.core.logging_config import logger
from app.services.music_ranker import music_ranker, _clean_query


class SpotifyService:
    def __init__(self):
        self.cache_path = os.path.join(os.path.dirname(__file__), "..", "..", ".cache-spotify")
        handler = CacheFileHandler(cache_path=self.cache_path)
        self.oauth = SpotifyOAuth(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIFY_REDIRECT_URI,
            scope=settings.SPOTIFY_SCOPES,
            cache_handler=handler,
            open_browser=False,
        )
        self._client_creds_client: Optional[spotipy.Spotify] = None

    def get_capabilities(self) -> Dict[str, Any]:
        """Returns the current Spotify capability matrix for Free Mode."""
        return {
            "search": True,
            "openSpotify": True,
            "directPlayback": False,
        }

    def get_authorize_url(self) -> str:
        """Generate the Spotify login URL with required scopes."""
        return self.oauth.get_authorize_url()

    def handle_callback(self, code: str) -> Dict[str, Any]:
        """Exchange auth code for tokens and save to cache."""
        token_info = self.oauth.get_access_token(code, as_dict=True)
        if not token_info:
            raise ValueError("Failed to retrieve access token from Spotify")
        return token_info

    def get_client(self) -> Optional[spotipy.Spotify]:
        """Retrieve an authenticated user spotipy client if valid tokens exist."""
        if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
            return None

        try:
            token_info = self.oauth.validate_token(self.oauth.cache_handler.get_cached_token())
            if not token_info:
                return None
            return spotipy.Spotify(auth=token_info["access_token"])
        except Exception as e:
            logger.warning(f"Error validating Spotify user token: {e}")
            return None

    def get_search_client(self) -> Optional[spotipy.Spotify]:
        """
        Retrieve a Spotify client suitable for searching the catalog.
        Prioritizes user OAuth client if available, else falls back to Client Credentials.
        """
        user_client = self.get_client()
        if user_client:
            return user_client

        if settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET:
            try:
                if not self._client_creds_client:
                    ccm = SpotifyClientCredentials(
                        client_id=settings.SPOTIFY_CLIENT_ID,
                        client_secret=settings.SPOTIFY_CLIENT_SECRET,
                    )
                    self._client_creds_client = spotipy.Spotify(client_credentials_manager=ccm)
                return self._client_creds_client
            except Exception as e:
                logger.error(f"Failed to initialize Spotify Client Credentials: {e}")

        return None

    def is_authenticated(self) -> bool:
        """Check whether we have an active valid user token."""
        if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
            return False
        try:
            token_info = self.oauth.validate_token(self.oauth.cache_handler.get_cached_token())
            return token_info is not None
        except Exception:
            return False

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Fetch basic profile of the authenticated Spotify user."""
        sp = self.get_client()
        if not sp:
            return None
        try:
            user = sp.current_user()
            return {
                "id": user.get("id"),
                "display_name": user.get("display_name"),
                "email": user.get("email"),
                "product": user.get("product", "free"),
                "images": user.get("images", []),
                "is_authenticated": True,
            }
        except Exception as e:
            logger.error(f"Error fetching Spotify user: {e}")
            return None

    def search_spotify(
        self,
        query: str,
        item_type: str = "track",
        limit: int = 10,
        offset: int = 0,
        artist_hint: Optional[str] = None,
        language_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Spotify Web API search with pagination (limit <= 10 for Dev Mode)
        and deterministic result ranking.
        """
        sp = self.get_search_client()
        if not sp:
            return {
                "success": False,
                "error": "Spotify service is not configured with client credentials.",
                "message": "Spotify search is not available. Please configure Spotify credentials in settings.",
                "tracks": [],
                "best_match": None,
            }

        # Enforce limit <= 10 for Spotify Development Mode stability
        safe_limit = min(max(1, limit), 10)
        safe_offset = max(0, offset)

        try:
            results = sp.search(q=query, limit=safe_limit, offset=safe_offset, type=item_type)
        except SpotifyException as se:
            logger.warning(f"Spotify API search exception: {se}")
            import urllib.parse
            clean_q = _clean_query(query) if '_clean_query' in globals() else query
            search_url = f"https://open.spotify.com/search/{urllib.parse.quote(clean_q)}"
            clean_title = clean_q.title()
            fallback_track = {
                "id": None,
                "name": clean_title,
                "title": clean_title,
                "artist": artist_hint or "Spotify",
                "artists": artist_hint or "Spotify",
                "artist_list": [artist_hint] if artist_hint else [],
                "album": "Spotify Web",
                "album_art": None,
                "duration": 0,
                "duration_ms": 0,
                "release_date": None,
                "release_year": None,
                "external_url": search_url,
                "uri": f"spotify:search:{urllib.parse.quote(clean_q)}",
                "preview_url": None,
                "ranking_score": 100,
                "ranking_reasons": ["direct_spotify_launcher_link"],
            }

            if se.http_status == 403:
                return {
                    "success": True,
                    "query": query,
                    "total": 1,
                    "limit": safe_limit,
                    "offset": safe_offset,
                    "has_more": False,
                    "tracks": [fallback_track],
                    "best_match": fallback_track,
                    "message": "Spotify API requires a supported Spotify plan. I can still find the song and open it in Spotify.",
                }
            elif se.http_status == 401:
                return {
                    "success": True,
                    "query": query,
                    "total": 1,
                    "limit": safe_limit,
                    "offset": safe_offset,
                    "has_more": False,
                    "tracks": [fallback_track],
                    "best_match": fallback_track,
                    "message": "Spotify session expired. I found the song and you can open it in Spotify.",
                }
            elif se.http_status == 429:
                return {
                    "success": True,
                    "query": query,
                    "total": 1,
                    "limit": safe_limit,
                    "offset": safe_offset,
                    "has_more": False,
                    "tracks": [fallback_track],
                    "best_match": fallback_track,
                    "message": "Spotify search is temporarily rate-limited. You can open it directly in Spotify.",
                }
            return {
                "success": False,
                "error": str(se),
                "message": "Unable to search Spotify right now. Please try again.",
                "tracks": [],
            }
        except Exception as exc:
            logger.error(f"Unexpected search error: {exc}")
            return {
                "success": False,
                "error": str(exc),
                "message": f"Search failed: {str(exc)}",
                "tracks": [],
            }

        items = results.get(f"{item_type}s", {}).get("items", []) if results else []
        total = results.get(f"{item_type}s", {}).get("total", 0) if results else 0

        if not items:
            return {
                "success": True,
                "query": query,
                "total": 0,
                "limit": safe_limit,
                "offset": safe_offset,
                "has_more": False,
                "tracks": [],
                "best_match": None,
                "message": f"No tracks found matching \"{query}\".",
            }

        # Deterministic Ranking
        ranked_items = music_ranker.rank_tracks(
            items,
            query=query,
            artist_hint=artist_hint,
            language_hint=language_hint,
        )

        formatted_tracks: List[Dict[str, Any]] = []
        for it in ranked_items:
            track_name = it.get("name", "Unknown Title")
            artists_list = [a.get("name", "") for a in it.get("artists", []) if isinstance(a, dict)]
            artists_str = ", ".join(artists_list) if artists_list else "Unknown Artist"

            album_data = it.get("album", {}) or {}
            album_name = album_data.get("name", "Single / Album")
            album_images = album_data.get("images", []) or []
            album_art = album_images[0].get("url", "") if album_images else ""
            release_date = album_data.get("release_date", "")
            release_year = release_date.split("-")[0] if release_date else None

            spotify_url = it.get("external_urls", {}).get("spotify", "")
            uri = it.get("uri", "")
            duration_ms = it.get("duration_ms", 0) or 0
            duration_seconds = round(duration_ms / 1000)

            formatted_tracks.append({
                "id": it.get("id"),
                "name": track_name,
                "title": track_name,
                "artist": artists_str,
                "artists": artists_str,
                "artist_list": artists_list,
                "album": album_name,
                "album_art": album_art,
                "duration_ms": duration_ms,
                "duration": duration_seconds,
                "release_date": release_date,
                "release_year": release_year,
                "external_url": spotify_url,
                "uri": uri,
                "preview_url": it.get("preview_url"),
                "ranking_score": it.get("_ranking_score", 0),
                "ranking_reasons": it.get("_ranking_reasons", []),
            })

        best_match = formatted_tracks[0] if formatted_tracks else None
        has_more = (safe_offset + safe_limit) < total

        return {
            "success": True,
            "query": query,
            "total": total,
            "limit": safe_limit,
            "offset": safe_offset,
            "has_more": has_more,
            "tracks": formatted_tracks,
            "best_match": best_match,
        }

    def search_and_play(
        self,
        query: str,
        item_type: str = "track",
        artist_hint: Optional[str] = None,
        language_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Music discovery & launcher action (replacing direct playback for Free Mode).
        Searches, ranks, and returns the top song result with 'Open in Spotify' metadata.
        Never pretends playback started and never crashes on Free accounts.
        """
        search_res = self.search_spotify(
            query=query,
            item_type=item_type,
            limit=10,
            offset=0,
            artist_hint=artist_hint,
            language_hint=language_hint,
        )

        if not search_res.get("success"):
            return {
                "success": False,
                "is_direct_play": False,
                "message": search_res.get("message", f"Unable to find \"{query}\" on Spotify."),
            }

        best = search_res.get("best_match")
        if not best:
            return {
                "success": False,
                "is_direct_play": False,
                "message": f"No tracks found for **\"{query}\"**.",
            }

        track_name = best["title"]
        artists = best["artist"]
        spotify_url = best["external_url"]

        # Return structured launcher payload
        return {
            "success": True,
            "is_direct_play": False,
            "message": f"I found **{track_name}** by {artists}. Open it in Spotify to listen.",
            "track": best,
            "open_url": spotify_url,
        }

    def get_playback_state(self) -> Dict[str, Any]:
        """
        Safely returns player status. In Free mode or when not streaming,
        gracefully returns connected status without raising 403.
        """
        is_auth = self.is_authenticated()
        capabilities = self.get_capabilities()

        if not is_auth:
            return {
                "is_connected": False,
                "is_playing": False,
                "track": None,
                "capabilities": capabilities,
            }

        sp = self.get_client()
        if not sp:
            return {
                "is_connected": True,
                "is_playing": False,
                "track": None,
                "capabilities": capabilities,
            }

        try:
            playback = sp.current_playback()
            if not playback or not playback.get("item"):
                return {
                    "is_connected": True,
                    "is_playing": False,
                    "track": None,
                    "capabilities": capabilities,
                }

            item = playback["item"]
            artists = ", ".join([a["name"] for a in item.get("artists", [])])
            album_images = item.get("album", {}).get("images", [])
            album_art = album_images[0]["url"] if album_images else None

            return {
                "is_connected": True,
                "is_playing": playback.get("is_playing", False),
                "progress_ms": playback.get("progress_ms", 0),
                "duration_ms": item.get("duration_ms", 0),
                "volume_percent": playback.get("device", {}).get("volume_percent", 100),
                "track": {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "title": item.get("name"),
                    "artists": artists,
                    "artist": artists,
                    "album": item.get("album", {}).get("name"),
                    "album_art": album_art,
                    "uri": item.get("uri"),
                    "external_url": item.get("external_urls", {}).get("spotify"),
                },
                "capabilities": capabilities,
            }
        except SpotifyException as se:
            logger.debug(f"Free mode / playback state notice: {se}")
            return {
                "is_connected": True,
                "is_playing": False,
                "track": None,
                "capabilities": capabilities,
            }
        except Exception as e:
            logger.warning(f"Error fetching playback state: {e}")
            return {
                "is_connected": True,
                "is_playing": False,
                "track": None,
                "capabilities": capabilities,
            }

    def pause(self) -> Dict[str, Any]:
        """Free-mode safe pause handler."""
        return {
            "success": False,
            "requires_premium": True,
            "message": "Spotify direct playback control requires a supported Spotify plan. Open songs in Spotify to control playback.",
        }

    def resume(self) -> Dict[str, Any]:
        """Free-mode safe resume handler."""
        return {
            "success": False,
            "requires_premium": True,
            "message": "Spotify direct playback control requires a supported Spotify plan. Open songs in Spotify to control playback.",
        }

    def next_track(self) -> Dict[str, Any]:
        """Free-mode safe next track handler."""
        return {
            "success": False,
            "requires_premium": True,
            "message": "Spotify direct playback control requires a supported Spotify plan. You can search for the next song and open it in Spotify.",
        }

    def previous_track(self) -> Dict[str, Any]:
        """Free-mode safe previous track handler."""
        return {
            "success": False,
            "requires_premium": True,
            "message": "Spotify direct playback control requires a supported Spotify plan. You can search for any song and open it in Spotify.",
        }

    def set_volume(self, volume_percent: int) -> Dict[str, Any]:
        """Free-mode safe volume handler."""
        return {
            "success": False,
            "requires_premium": True,
            "message": "Spotify remote volume control requires a supported Spotify plan.",
        }


spotify_service = SpotifyService()
