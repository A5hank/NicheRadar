"""Command-line interface for running a complete niche analysis."""

import argparse

from nicheradar.config import get_settings
from nicheradar.database import (
    create_database_engine,
    create_database_schema,
    create_session_factory,
)
from nicheradar.pipeline import (
    DEFAULT_SEARCH_LIMIT,
    NicheAnalysis,
    run_niche_analysis,
)

from nicheradar.groq_client import GroqClient
from nicheradar.query_expansion import (
    DEFAULT_QUERY_COUNT,
    expand_niche_queries,
)
from nicheradar.query_review import review_queries_interactively

from nicheradar.ranking import ScoredVideo
from nicheradar.results import DEFAULT_RESULT_LIMIT
from nicheradar.youtube import YouTubeClient

MAX_COMMAND_LIMIT = 50


def parse_niche(value: str) -> str:
    """Validate and clean the niche entered by the user."""

    niche = value.strip()

    if not niche:
        raise argparse.ArgumentTypeError("niche must not be empty")

    return niche


def parse_limit(value: str) -> int:
    """Convert a command-line limit into an integer from 1 to 50."""

    try:
        limit = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("limit must be an integer") from error

    if not 1 <= limit <= MAX_COMMAND_LIMIT:
        raise argparse.ArgumentTypeError(f"limit must be between 1 and {MAX_COMMAND_LIMIT}")

    return limit


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description=("Collect and analyze recent YouTube Short candidates for a niche.")
    )

    parser.add_argument(
        "niche",
        type=parse_niche,
        help='Niche to analyze, such as "AI productivity".',
    )

    parser.add_argument(
        "--search-limit",
        type=parse_limit,
        default=DEFAULT_SEARCH_LIMIT,
        help=(
            f"Maximum number of YouTube search results to collect. Default: {DEFAULT_SEARCH_LIMIT}."
        ),
    )

    parser.add_argument(
        "--result-limit",
        type=parse_limit,
        default=DEFAULT_RESULT_LIMIT,
        help=(f"Maximum number of ranked videos to display. Default: {DEFAULT_RESULT_LIMIT}."),
    )

    return parser


def format_integer(value: int | None) -> str:
    """Format an integer with commas or show that it is unavailable."""

    if value is None:
        return "unavailable"

    return f"{value:,}"


def format_decimal(value: float) -> str:
    """Format a decimal value with commas and two decimal places."""

    return f"{value:,.2f}"


def format_multiplier(value: float | None) -> str:
    """Format a subscriber multiplier such as 25.40x."""

    if value is None:
        return "unavailable"

    return f"{value:,.2f}x"


def performance_badge(scored_video: ScoredVideo) -> str:
    """Return a visual label for exceptional or breakout performance."""

    metrics = scored_video.metrics

    if metrics.is_exceptional_performance:
        return "[EXCEPTIONAL PERFORMANCE]"

    if metrics.is_breakout:
        return "[BREAKOUT]"

    return ""


def build_analysis_report(
    analysis: NicheAnalysis,
) -> str:
    """Convert a completed niche analysis into printable text."""

    collection = analysis.collection
    results = analysis.results

    breakout_count = sum(scored_video.metrics.is_breakout for scored_video in results.videos)
    exceptional_count = sum(
        scored_video.metrics.is_exceptional_performance for scored_video in results.videos
    )

    lines = [
        "",
        f"NicheRadar analysis: {collection.niche}",
        "=" * 70,
        f"Videos considered: {results.considered_count}",
        f"Videos saved: {collection.saved_count}",
        f"Videos returned: {len(results.videos)}",
        f"Breakout highlights: {breakout_count}",
        f"Exceptional-performance highlights: {exceptional_count}",
    ]

    if not results.videos:
        lines.extend(
            [
                "",
                "No qualifying Short candidates were found.",
            ]
        )
        return "\n".join(lines)

    for position, scored_video in enumerate(
        results.videos,
        start=1,
    ):
        metrics = scored_video.metrics
        badge = performance_badge(scored_video)

        heading = f"{position}. {scored_video.title}"

        if badge:
            heading = f"{heading} {badge}"

        lines.extend(
            [
                "",
                "-" * 70,
                heading,
                f"   Channel: {scored_video.channel_name}",
                (
                    f"   Views: "
                    f"{format_integer(scored_video.views)}"
                    " | "
                    f"Subscribers: "
                    f"{format_integer(scored_video.subscribers)}"
                ),
                (
                    f"   Views/day: "
                    f"{format_decimal(metrics.views_per_day)}"
                    " | "
                    f"Subscriber multiplier: "
                    f"{format_multiplier(metrics.subscriber_multiplier)}"
                ),
                f"   Link: {scored_video.url}",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    """Run a complete niche analysis from the command line."""

    parser = build_argument_parser()
    arguments = parser.parse_args()
    settings = get_settings()

    if not settings.youtube_api_key:
        parser.error("YOUTUBE_API_KEY is missing. Add it to your .env file.")

    if not settings.groq_api_key:
        raise SystemExit(
            "GROQ_API_KEY is missing. Add it to your .env file."
        )

    with GroqClient(settings.groq_api_key) as groq_client:
        expansion = expand_niche_queries(
            groq_client,
            arguments.niche,
            query_count=DEFAULT_QUERY_COUNT,
        )

    approved_queries = review_queries_interactively(
        niche=expansion.niche,
        suggested_queries=expansion.queries,
    )

    engine = create_database_engine(settings.database_url)

    try:
        create_database_schema(engine)
        session_factory = create_session_factory(engine)

        with YouTubeClient(settings.youtube_api_key) as client:
            with session_factory.begin() as session:
                analysis = run_niche_analysis(
                    client=client,
                    session=session,
                    niche=expansion.niche,
                    search_queries=approved_queries,
                    search_limit=arguments.search_limit,
                    result_limit=arguments.result_limit,
                )

                report = build_analysis_report(analysis)
    finally:
        engine.dispose()

    print(report)


if __name__ == "__main__":
    main()
