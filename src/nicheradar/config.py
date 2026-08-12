"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = "sqlite:///data/nicheradar.db"


@dataclass(frozen=True)
class Settings:
    """Configuration values required by NicheRadar."""

    youtube_api_key: str | None
    groq_api_key: str | None
    database_url: str
    app_env: str


def _optional_env(name: str) -> str | None:
    """Return a cleaned environment variable or None if it is empty."""

    value = os.getenv(name)

    if value is None:
        return None

    cleaned_value = value.strip()
    return cleaned_value or None


def get_settings(
    env_file: Path | None = PROJECT_ROOT / ".env",
) -> Settings:
    """Load configuration and return it as a Settings object."""

    if env_file is not None:
        load_dotenv(env_file, override=False)

    return Settings(
        youtube_api_key=_optional_env("YOUTUBE_API_KEY"),
        groq_api_key=_optional_env("GROQ_API_KEY"),
        database_url=os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL,
        app_env=os.getenv("APP_ENV") or "development",
    )
