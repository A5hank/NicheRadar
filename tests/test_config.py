"""Tests for NicheRadar configuration."""

import pytest

from nicheradar.config import (
    DEFAULT_DATABASE_URL,
    PROJECT_ROOT,
    get_settings,
)


def test_settings_use_safe_defaults(monkeypatch) -> None:
    """Missing environment variables should produce safe defaults."""

    variables = (
        "YOUTUBE_API_KEY",
        "GROQ_API_KEY",
        "DATABASE_URL",
        "APP_ENV",
    )

    for variable in variables:
        monkeypatch.delenv(variable, raising=False)

    settings = get_settings(env_file=None)

    assert settings.youtube_api_key is None
    assert settings.groq_api_key is None
    assert settings.database_url == DEFAULT_DATABASE_URL
    assert settings.app_env == "development"


def test_settings_read_environment_variables(monkeypatch) -> None:
    """System environment variables should override default values."""

    monkeypatch.setenv("YOUTUBE_API_KEY", "youtube-test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://localhost/nicheradar_test",
    )
    monkeypatch.setenv("APP_ENV", "test")

    settings = get_settings(env_file=None)

    assert settings.youtube_api_key == "youtube-test-key"
    assert settings.groq_api_key == "groq-test-key"
    assert settings.database_url == "postgresql+psycopg://localhost/nicheradar_test"
    assert settings.app_env == "test"


def test_relative_sqlite_path_uses_project_root(
    monkeypatch,
    tmp_path,
) -> None:
    """SQLite paths must not depend on the terminal directory."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(
        "DATABASE_URL",
        "sqlite:///data/custom.db",
    )

    settings = get_settings(env_file=None)

    expected_path = (PROJECT_ROOT / "data" / "custom.db").resolve()

    expected_url = f"sqlite:///{expected_path.as_posix()}"

    assert settings.database_url == expected_url


def test_production_settings_require_managed_database_and_secrets(monkeypatch) -> None:
    """Production must never silently fall back to local SQLite or missing controls."""

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_MODE", "public_beta")
    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/nicheradar")
    monkeypatch.setenv("YOUTUBE_API_KEY", "youtube-test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.setenv("CRON_SECRET", "cron-test-secret")

    settings = get_settings(env_file=None)

    assert settings.database_url == "postgresql+psycopg://localhost/nicheradar"


def test_production_settings_reject_sqlite(monkeypatch) -> None:
    """A deployed instance should fail closed instead of storing data on disk."""

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_MODE", "public_beta")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/nicheradar.db")
    monkeypatch.setenv("YOUTUBE_API_KEY", "youtube-test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.setenv("CRON_SECRET", "cron-test-secret")

    with pytest.raises(ValueError, match="managed PostgreSQL"):
        get_settings(env_file=None)
