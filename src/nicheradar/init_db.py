"""Create the local NicheRadar database schema."""

from nicheradar.config import get_settings
from nicheradar.database import (
    check_database_connection,
    create_database_engine,
    create_database_schema,
)


def main() -> None:
    """Create missing database tables and verify connectivity."""

    settings = get_settings()
    engine = create_database_engine(settings.database_url)

    try:
        create_database_schema(engine)

        if not check_database_connection(engine):
            raise RuntimeError("Database connection check failed.")

        print("NicheRadar database schema created successfully.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
