"""Tests for controlled schema initialization outside request handling."""

from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from nicheradar.database import create_database_engine
from nicheradar.init_db import run_database_migrations


def test_migrations_create_active_runtime_tables(tmp_path) -> None:
    """A fresh local database should be initialized by Alembic, not an API request."""

    database_path = tmp_path / "nicheradar.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    run_database_migrations(database_url)

    engine = create_database_engine(database_url)

    try:
        assert set(inspect(engine).get_table_names()) == {
            "alembic_version",
            "analysis_locks",
            "analysis_runs",
            "analysis_snapshots",
            "analysis_videos",
            "request_rate_limits",
            "youtube_daily_budgets",
        }
    finally:
        engine.dispose()


def test_migration_compiles_for_postgresql_without_identifier_errors() -> None:
    """The deployment migration must respect PostgreSQL's identifier limits."""

    project_root = Path(__file__).resolve().parents[1]
    alembic_config = Config(
        str(project_root / "alembic.ini"),
        output_buffer=StringIO(),
    )
    alembic_config.set_main_option(
        "sqlalchemy.url",
        "postgresql+psycopg://user:password@localhost/nicheradar",
    )

    command.upgrade(
        alembic_config,
        "head",
        sql=True,
    )
