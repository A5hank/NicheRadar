"""Temporary command-line entry point for NicheRadar."""

from nicheradar.config import Settings, get_settings


def build_status_message(settings: Settings | None = None) -> str:
    """Build a safe startup message without exposing credentials."""

    current_settings = settings or get_settings()

    return f"NicheRadar is ready (environment={current_settings.app_env})"


def main() -> None:
    """Start the current version of the application."""

    print(build_status_message())
