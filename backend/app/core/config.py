import json
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Zana AI Assistant"
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    
    # CORS origins
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Spotify Configuration
    SPOTIFY_CLIENT_ID: str = ""
    SPOTIFY_CLIENT_SECRET: str = ""
    SPOTIFY_REDIRECT_URI: str = "http://127.0.0.1:8000/api/spotify/callback"
    SPOTIFY_FRONTEND_REDIRECT: str = "http://localhost:5173"
    SPOTIFY_SCOPES: str = (
        "user-read-playback-state "
        "user-modify-playback-state "
        "user-read-currently-playing "
        "streaming "
        "playlist-read-private "
        "playlist-modify-public "
        "playlist-modify-private "
        "user-read-recently-played"
    )


    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()
