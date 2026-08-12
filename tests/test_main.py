"""Tests for the NicheRadar application entry point."""

from nicheradar.config import Settings
from nicheradar.main import build_status_message


def test_status_message_does_not_expose_secrets() -> None:
    """Startup messages must never leak credentials."""

    settings = Settings(
        youtube_api_key="youtube-secret",
        groq_api_key="groq-secret",
        database_url=("postgresql://database-user:database-password@localhost/nicheradar"),
        app_env="test",
    )

    message = build_status_message(settings)

    assert message == "NicheRadar is ready (environment=test)"
    assert "youtube-secret" not in message
    assert "groq-secret" not in message
    assert "database-password" not in message
