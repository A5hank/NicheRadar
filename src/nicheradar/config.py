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

DEFAULT_APP_ENV = "development"
DEFAULT_APP_MODE = "local"
DEFAULT_ANALYSIS_TIMEOUT_SECONDS = 45.0
DEFAULT_YOUTUBE_TIMEOUT_SECONDS = 8.0
DEFAULT_GROQ_TIMEOUT_SECONDS = 10.0
DEFAULT_YOUTUBE_DAILY_SEARCH_BUDGET = 80
DEFAULT_RATE_LIMIT_PER_MINUTE = 10
DEFAULT_ANALYSIS_RATE_LIMIT_PER_MINUTE = 2
PRODUCTION_APP_MODES = frozenset({"private_staging", "public_beta"})


@dataclass(frozen=True, slots=True)
class Settings:
    """Typed configuration used by the application."""

    youtube_api_key: str | None
    groq_api_key: str | None
    database_url: str
    app_env: str
    app_mode: str = DEFAULT_APP_MODE
    analysis_timeout_seconds: float = DEFAULT_ANALYSIS_TIMEOUT_SECONDS
    youtube_timeout_seconds: float = DEFAULT_YOUTUBE_TIMEOUT_SECONDS
    groq_timeout_seconds: float = DEFAULT_GROQ_TIMEOUT_SECONDS
    youtube_daily_search_budget: int = DEFAULT_YOUTUBE_DAILY_SEARCH_BUDGET
    rate_limit_per_minute: int = DEFAULT_RATE_LIMIT_PER_MINUTE
    analysis_rate_limit_per_minute: int = DEFAULT_ANALYSIS_RATE_LIMIT_PER_MINUTE
    cron_secret: str | None = None


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

    if cleaned_url.startswith("postgres://"):
        return f"postgresql+psycopg://{cleaned_url.removeprefix('postgres://')}"

    if cleaned_url.startswith("postgresql://"):
        return f"postgresql+psycopg://{cleaned_url.removeprefix('postgresql://')}"

    return cleaned_url


def _positive_int_env(name: str, default: int) -> int:
    """Read a positive integer setting or raise a clear configuration error."""

    raw_value = os.getenv(name)

    if raw_value is None or not raw_value.strip():
        return default

    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be a positive integer") from error

    if value < 1:
        raise ValueError(f"{name} must be a positive integer")

    return value


def _positive_float_env(name: str, default: float) -> float:
    """Read a positive floating-point setting or raise a clear configuration error."""

    raw_value = os.getenv(name)

    if raw_value is None or not raw_value.strip():
        return default

    try:
        value = float(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be a positive number") from error

    if value <= 0:
        raise ValueError(f"{name} must be a positive number")

    return value


def validate_production_settings(settings: Settings) -> Settings:
    """Reject unsafe production configuration before any provider call occurs."""

    if settings.app_env != "production":
        return settings

    missing_names = [
        name
        for name, value in (
            ("YOUTUBE_API_KEY", settings.youtube_api_key),
            ("GROQ_API_KEY", settings.groq_api_key),
            ("CRON_SECRET", settings.cron_secret),
        )
        if not value
    ]

    if missing_names:
        raise ValueError("Production configuration is missing: " + ", ".join(missing_names))

    if settings.database_url.startswith(SQLITE_URL_PREFIXES):
        raise ValueError("Production DATABASE_URL must use managed PostgreSQL")

    if settings.app_mode not in PRODUCTION_APP_MODES:
        raise ValueError("Production APP_MODE must be private_staging or public_beta")

    return settings


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

    settings = Settings(
        youtube_api_key=_optional_env("YOUTUBE_API_KEY"),
        groq_api_key=_optional_env("GROQ_API_KEY"),
        database_url=_resolve_database_url(raw_database_url),
        app_env=(os.getenv("APP_ENV") or DEFAULT_APP_ENV),
        app_mode=(os.getenv("APP_MODE") or DEFAULT_APP_MODE),
        analysis_timeout_seconds=_positive_float_env(
            "ANALYSIS_TIMEOUT_SECONDS",
            DEFAULT_ANALYSIS_TIMEOUT_SECONDS,
        ),
        youtube_timeout_seconds=_positive_float_env(
            "YOUTUBE_TIMEOUT_SECONDS",
            DEFAULT_YOUTUBE_TIMEOUT_SECONDS,
        ),
        groq_timeout_seconds=_positive_float_env(
            "GROQ_TIMEOUT_SECONDS",
            DEFAULT_GROQ_TIMEOUT_SECONDS,
        ),
        youtube_daily_search_budget=_positive_int_env(
            "YOUTUBE_DAILY_SEARCH_BUDGET",
            DEFAULT_YOUTUBE_DAILY_SEARCH_BUDGET,
        ),
        rate_limit_per_minute=_positive_int_env(
            "RATE_LIMIT_PER_MINUTE",
            DEFAULT_RATE_LIMIT_PER_MINUTE,
        ),
        analysis_rate_limit_per_minute=_positive_int_env(
            "ANALYSIS_RATE_LIMIT_PER_MINUTE",
            DEFAULT_ANALYSIS_RATE_LIMIT_PER_MINUTE,
        ),
        cron_secret=_optional_env("CRON_SECRET"),
    )

    return validate_production_settings(settings)
