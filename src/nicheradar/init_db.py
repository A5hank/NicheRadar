"""Apply controlled NicheRadar database migrations."""

from pathlib import Path

from alembic import command
from alembic.config import Config

from nicheradar.config import get_settings
from nicheradar.database import (
    check_database_connection,
    create_database_engine,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_database_migrations(database_url: str) -> None:
    """Upgrade one configured database to the latest controlled revision."""

    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")


def main() -> None:
    """Upgrade the configured database and verify connectivity."""

    settings = get_settings()
    engine = create_database_engine(settings.database_url)

    try:
        run_database_migrations(settings.database_url)

        if not check_database_connection(engine):
            raise RuntimeError("Database connection check failed.")

        print("NicheRadar database migrations applied successfully.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
