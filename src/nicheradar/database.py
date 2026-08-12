"""SQLAlchemy engine and session configuration."""

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker


def create_database_engine(
    database_url: str,
    *,
    echo: bool = False,
) -> Engine:
    """Create a SQLAlchemy engine for the supplied database URL."""

    return create_engine(
        database_url,
        echo=echo,
        hide_parameters=True,
        pool_pre_ping=True,
    )


def create_session_factory(
    engine: Engine,
) -> sessionmaker[Session]:
    """Create a factory that produces database sessions."""

    return sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


def check_database_connection(engine: Engine) -> bool:
    """Run a minimal query to verify database connectivity."""

    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()

    return result == 1
