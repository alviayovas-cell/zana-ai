import yt_dlp
from typing import Optional, Dict, Any
from app.core.logging_config import logger


class FreeMusicService:
    """
    100% Free Music Streaming & Search Service using yt-dlp.
    Extracts direct audio streams without requiring Spotify Premium or API keys.
    """

    def __init__(self):
        self.ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "default_search": "ytsearch1",
            "socket_timeout": 10,
        }

    def search_and_extract(self, query: str) -> Optional[Dict[str, Any]]:
        """Search query on YouTube Music / YouTube and extract the streaming audio URL."""
        search_term = f"ytsearch1:{query} audio"
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(search_term, download=False)
                if not info:
                    return None

                entries = info.get("entries")
                entry = entries[0] if entries else info

                # Extract best audio stream url
                audio_url = entry.get("url")
                if not audio_url and "formats" in entry:
                    # Pick best audio-only format
                    audio_formats = [
                        f for f in entry["formats"]
                        if f.get("acodec") != "none" and f.get("vcodec") == "none"
                    ]
                    if audio_formats:
                        audio_url = audio_formats[-1].get("url")
                    else:
                        audio_url = entry["formats"][-1].get("url")

                title = entry.get("title", query)
                uploader = entry.get("uploader") or entry.get("channel") or "Unknown Artist"
                thumbnail = entry.get("thumbnail") or (entry.get("thumbnails", [{}])[-1].get("url"))
                duration = entry.get("duration", 0)
                video_id = entry.get("id")

                # Clean up title (remove "(Official Audio)", etc. for clean UI display)
                clean_title = title
                for tag in ["(Official Audio)", "(Official Music Video)", "[Official Video]", "(Audio)", "[Audio]", "(Lyric Video)", "(Lyrics)"]:
                    clean_title = clean_title.replace(tag, "").strip()

                return {
                    "id": video_id,
                    "title": clean_title,
                    "artist": uploader,
                    "album_art": thumbnail,
                    "audio_url": audio_url,
                    "duration": duration,
                    "webpage_url": entry.get("webpage_url", f"https://www.youtube.com/watch?v={video_id}"),
                }
        except Exception as e:
            logger.error(f"FreeMusicService error searching '{query}': {e}")
            return None


free_music_service = FreeMusicService()
