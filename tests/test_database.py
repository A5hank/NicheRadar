"""Tests for the SQLAlchemy database foundation."""

from sqlalchemy import text

from nicheradar.database import (
    check_database_connection,
    create_database_engine,
    create_session_factory,
)


def test_engine_connects_to_in_memory_sqlite() -> None:
    """The engine should communicate with an SQLite database."""

    engine = create_database_engine("sqlite+pysqlite:///:memory:")

    try:
        assert engine.dialect.name == "sqlite"
        assert check_database_connection(engine) is True
    finally:
        engine.dispose()


def test_session_factory_creates_working_sessions() -> None:
    """Sessions produced by the factory should execute database queries."""

    engine = create_database_engine("sqlite+pysqlite:///:memory:")

    try:
        session_factory = create_session_factory(engine)

        with session_factory() as session:
            result = session.execute(text("SELECT 42")).scalar_one()

        assert result == 42
    finally:
        engine.dispose()
