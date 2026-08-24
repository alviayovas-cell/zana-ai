import os
from typing import Optional, Dict, Any, List
import spotipy
from spotipy.oauth2 import SpotifyOAuth, CacheFileHandler
from spotipy.exceptions import SpotifyException

from app.core.config import settings
from app.core.logging_config import logger


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
        """Retrieve an authenticated spotipy client if valid tokens exist."""
        if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
            return None

        token_info = self.oauth.validate_token(self.oauth.cache_handler.get_cached_token())
        if not token_info:
            return None

        return spotipy.Spotify(auth=token_info["access_token"])

    def is_authenticated(self) -> bool:
        """Check whether we have an active valid token."""
        if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
            return False
        token_info = self.oauth.validate_token(self.oauth.cache_handler.get_cached_token())
        return token_info is not None

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
                "product": user.get("product"),
                "images": user.get("images", []),
                "is_authenticated": True,
            }
        except Exception as e:
            logger.error(f"Error fetching Spotify user: {e}")
            return None

    def get_devices(self) -> List[Dict[str, Any]]:
        """List available playback devices."""
        sp = self.get_client()
        if not sp:
            return []
        try:
            res = sp.devices()
            return res.get("devices", [])
        except Exception as e:
            logger.error(f"Error getting Spotify devices: {e}")
            return []

    def get_playback_state(self) -> Dict[str, Any]:
        """Fetch current playing track and player status."""
        sp = self.get_client()
        if not sp:
            return {"is_connected": False, "is_playing": False, "track": None}

        try:
            playback = sp.current_playback()
            if not playback or not playback.get("item"):
                return {
                    "is_connected": True,
                    "is_playing": False,
                    "track": None,
                    "device": playback.get("device") if playback else None,
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
                "shuffle_state": playback.get("shuffle_state", False),
                "repeat_state": playback.get("repeat_state", "off"),
                "track": {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "artists": artists,
                    "album": item.get("album", {}).get("name"),
                    "album_art": album_art,
                    "uri": item.get("uri"),
                    "external_url": item.get("external_urls", {}).get("spotify"),
                },
                "device": playback.get("device"),
            }
        except Exception as e:
            logger.error(f"Error getting playback state: {e}")
            return {"is_connected": True, "is_playing": False, "error": str(e), "track": None}

    def search_and_play(self, query: str, item_type: str = "track") -> Dict[str, Any]:
        """Search Spotify for a track/artist/album/playlist and start playing."""
        sp = self.get_client()
        if not sp:
            return {"success": False, "message": "Spotify is not connected. Please connect your account first."}

        try:
            # Check devices
            devices = self.get_devices()
            active_device = next((d for d in devices if d.get("is_active")), None)
            device_id = active_device["id"] if active_device else (devices[0]["id"] if devices else None)

            # Search query
            results = sp.search(q=query, limit=1, type=item_type)
            items = results.get(f"{item_type}s", {}).get("items", [])

            if not items:
                return {"success": False, "message": f"No {item_type} found for \"{query}\"."}

            item = items[0]
            track_name = item.get("name")
            artists = ", ".join([a["name"] for a in item.get("artists", [])]) if "artists" in item else ""
            album_art = item.get("album", {}).get("images", [{}])[0].get("url", "") if "album" in item else ""
            spotify_url = item.get("external_urls", {}).get("spotify", "")
            preview_url = item.get("preview_url")

            # Try to trigger active device playback
            try:
                if item_type == "track":
                    sp.start_playback(device_id=device_id, uris=[item["uri"]])
                else:
                    sp.start_playback(device_id=device_id, context_uri=item["uri"])

                return {
                    "success": True,
                    "message": f"Playing **{track_name}** by {artists}",
                    "track": {
                        "name": track_name,
                        "artists": artists,
                        "album_art": album_art,
                        "uri": item.get("uri"),
                        "external_url": spotify_url,
                        "preview_url": preview_url,
                    }
                }
            except SpotifyException as se:
                logger.warning(f"Playback trigger note: {se}")
                # If Spotify Free or no active device, still provide track info & direct play link!
                return {
                    "success": True,
                    "is_direct_play": False,
                    "message": (
                        f"🎵 Found **{track_name}** by **{artists}**!\n\n"
                        f"▶️ [Click to Open & Play on Spotify]({spotify_url})\n\n"
                        f"*(Note: Spotify requires Spotify Premium or an already-playing Spotify app to trigger background playback automatically.)*"
                    ),
                    "track": {
                        "name": track_name,
                        "artists": artists,
                        "album_art": album_art,
                        "uri": item.get("uri"),
                        "external_url": spotify_url,
                        "preview_url": preview_url,
                    }
                }

        except Exception as e:
            logger.error(f"Playback error: {e}")
            return {"success": False, "message": f"Unable to start playback: {str(e)}"}

    def pause(self) -> Dict[str, Any]:
        """Pause playback."""
        sp = self.get_client()
        if not sp:
            return {"success": False, "message": "Spotify not connected."}
        try:
            sp.pause_playback()
            return {"success": True, "message": "Playback paused."}
        except Exception as e:
            return {"success": False, "message": f"Could not pause: {str(e)}"}

    def resume(self) -> Dict[str, Any]:
        """Resume playback."""
        sp = self.get_client()
        if not sp:
            return {"success": False, "message": "Spotify not connected."}
        try:
            sp.start_playback()
            return {"success": True, "message": "Playback resumed."}
        except Exception as e:
            return {"success": False, "message": f"Could not resume: {str(e)}"}

    def next_track(self) -> Dict[str, Any]:
        """Skip to next track."""
        sp = self.get_client()
        if not sp:
            return {"success": False, "message": "Spotify not connected."}
        try:
            sp.next_track()
            return {"success": True, "message": "Skipped to next track."}
        except Exception as e:
            return {"success": False, "message": f"Could not skip track: {str(e)}"}

    def previous_track(self) -> Dict[str, Any]:
        """Return to previous track."""
        sp = self.get_client()
        if not sp:
            return {"success": False, "message": "Spotify not connected."}
        try:
            sp.previous_track()
            return {"success": True, "message": "Playing previous track."}
        except Exception as e:
            return {"success": False, "message": f"Could not go to previous track: {str(e)}"}

    def set_volume(self, volume_percent: int) -> Dict[str, Any]:
        """Set volume percentage (0-100)."""
        sp = self.get_client()
        if not sp:
            return {"success": False, "message": "Spotify not connected."}
        try:
            clamped = max(0, min(100, volume_percent))
            sp.volume(clamped)
            return {"success": True, "message": f"Volume set to {clamped}%."}
        except Exception as e:
            return {"success": False, "message": f"Could not set volume: {str(e)}"}


spotify_service = SpotifyService()
