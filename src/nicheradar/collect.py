"""Run a NicheRadar YouTube collection."""

import argparse

from nicheradar.collector import collect_niche
from nicheradar.config import get_settings
from nicheradar.database import (
    create_database_engine,
    create_database_schema,
    create_session_factory,
)
from nicheradar.youtube import YouTubeClient


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description=("Collect recent YouTube Short candidates for a niche.")
    )
    parser.add_argument(
        "niche",
        help='Niche to collect, such as "AI productivity".',
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        help="Maximum search results from 1 to 50.",
    )

    return parser


def main() -> None:
    """Collect and save one niche search."""

    arguments = build_argument_parser().parse_args()
    settings = get_settings()

    if not settings.youtube_api_key:
        raise RuntimeError("YOUTUBE_API_KEY is missing from the environment.")

    engine = create_database_engine(settings.database_url)

    try:
        create_database_schema(engine)
        session_factory = create_session_factory(engine)

        with YouTubeClient(settings.youtube_api_key) as client:
            with session_factory.begin() as session:
                summary = collect_niche(
                    client=client,
                    session=session,
                    niche=arguments.niche,
                    max_results=arguments.max_results,
                )
    finally:
        engine.dispose()

    print("NicheRadar collection completed.")
    print(f"Niche: {summary.niche}")
    print(f"Search results: {summary.searched_count}")
    print(f"Metadata fetched: {summary.fetched_count}")
    print(f"Short candidates: {summary.short_candidate_count}")
    print(f"Saved: {summary.saved_count}")
    print(f"Skipped: {summary.skipped_count}")


if __name__ == "__main__":
    main()
