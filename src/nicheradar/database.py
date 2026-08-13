"""SQLAlchemy engine, schema, and session configuration."""

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from nicheradar.models import Base


def create_database_engine(
    database_url: str,
    *,
    echo: bool = False,
) -> Engine:
    """Create a SQLAlchemy engine for the supplied database URL."""

    engine = create_engine(
        database_url,
        echo=echo,
        hide_parameters=True,
        pool_pre_ping=True,
    )

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(
            dbapi_connection,
            _connection_record,
        ) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(
    engine: Engine,
) -> sessionmaker[Session]:
    """Create a factory that produces database sessions."""

    return sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


def create_database_schema(engine: Engine) -> None:
    """Create every missing NicheRadar database table."""

    Base.metadata.create_all(engine)


def check_database_connection(engine: Engine) -> bool:
    """Run a minimal query to verify database connectivity."""

    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()

    return result == 1
