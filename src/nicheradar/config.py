"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = (PROJECT_ROOT / "data" / "nicheradar.db").resolve()
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"

SQLITE_URL_PREFIXES = (
    "sqlite+pysqlite:///",
    "sqlite:///",
)


@dataclass(frozen=True, slots=True)
class Settings:
    """Typed configuration used by the application."""

    youtube_api_key: str | None
    groq_api_key: str | None
    database_url: str
    app_env: str


def _optional_env(name: str) -> str | None:
    """Return an environment variable, treating an empty value as missing."""

    return os.getenv(name) or None


def _resolve_database_url(
    database_url: str,
) -> str:
    """Resolve relative SQLite paths from the project root."""

    cleaned_url = database_url.strip()

    for prefix in SQLITE_URL_PREFIXES:
        if not cleaned_url.startswith(prefix):
            continue

        database_path_text = cleaned_url[len(prefix) :]

        if database_path_text == ":memory:":
            return cleaned_url

        database_path = Path(database_path_text)

        if database_path.is_absolute():
            return cleaned_url

        resolved_path = (PROJECT_ROOT / database_path).resolve()

        return f"{prefix}{resolved_path.as_posix()}"

    return cleaned_url


def get_settings(
    env_file: Path | None = PROJECT_ROOT / ".env",
) -> Settings:
    """Load environment values and return typed settings.

    Existing operating-system variables win over `.env` values. Relative
    SQLite paths are resolved from the project root rather than the terminal's
    current working directory.
    """

    if env_file is not None:
        load_dotenv(
            env_file,
            override=False,
        )

    raw_database_url = os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL

    return Settings(
        youtube_api_key=_optional_env("YOUTUBE_API_KEY"),
        groq_api_key=_optional_env("GROQ_API_KEY"),
        database_url=_resolve_database_url(raw_database_url),
        app_env=(os.getenv("APP_ENV") or "development"),
    )
