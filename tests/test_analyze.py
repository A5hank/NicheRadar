"""Tests for the NicheRadar analysis command."""

import argparse
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

import pytest

from nicheradar.analytics import PerformanceMetrics
from nicheradar.analyze import (
    build_analysis_report,
    build_argument_parser,
    parse_limit,
    parse_niche,
)
from nicheradar.ranking import ScoredVideo


def make_scored_video(
    *,
    video_id: str,
    title: str,
    views: int,
    subscribers: int | None,
    views_per_day: float,
    subscriber_multiplier: float | None,
    is_breakout: bool = False,
    is_exceptional: bool = False,
) -> ScoredVideo:
    """Create a scored video for report-formatting tests."""

    metrics = cast(
        PerformanceMetrics,
        SimpleNamespace(
            views_per_day=views_per_day,
            subscriber_multiplier=subscriber_multiplier,
            is_breakout=is_breakout,
            is_exceptional_performance=is_exceptional,
        ),
    )

    return ScoredVideo(
        video_id=video_id,
        title=title,
        url=(f"https://www.youtube.com/watch?v={video_id}"),
        channel_id="channel-123",
        channel_name="Test Channel",
        upload_date=datetime(
            2026,
            8,
            14,
            12,
            0,
            tzinfo=UTC,
        ),
        views=views,
        subscribers=subscribers,
        metrics=metrics,
    )


def test_parse_niche_removes_surrounding_spaces() -> None:
    """Niche input should be cleaned before analysis."""

    assert parse_niche("  AI productivity  ") == ("AI productivity")


def test_parse_niche_rejects_empty_text() -> None:
    """An empty niche should be rejected."""

    with pytest.raises(argparse.ArgumentTypeError):
        parse_niche("   ")


@pytest.mark.parametrize(
    "value",
    ["0", "51", "not-a-number"],
)
def test_parse_limit_rejects_invalid_values(
    value: str,
) -> None:
    """Limits must be integers between 1 and 50."""

    with pytest.raises(argparse.ArgumentTypeError):
        parse_limit(value)


def test_argument_parser_reads_command_options() -> None:
    """The parser should convert terminal arguments correctly."""

    parser = build_argument_parser()

    arguments = parser.parse_args(
        [
            "AI productivity",
            "--search-limit",
            "40",
            "--result-limit",
            "20",
        ]
    )

    assert arguments.niche == "AI productivity"
    assert arguments.search_limit == 40
    assert arguments.result_limit == 20


def test_build_analysis_report_preserves_result_order() -> None:
    """Formatting should not reorder videos based on highlights."""

    regular = make_scored_video(
        video_id="regular-123",
        title="Regular high-view video",
        views=500_000,
        subscribers=200_000,
        views_per_day=300_000.0,
        subscriber_multiplier=2.5,
    )
    breakout = make_scored_video(
        video_id="breakout-123",
        title="Small-channel breakout",
        views=250_000,
        subscribers=5_000,
        views_per_day=250_000.0,
        subscriber_multiplier=50.0,
        is_breakout=True,
    )
    exceptional = make_scored_video(
        video_id="exceptional-123",
        title="Large-channel exceptional video",
        views=200_000,
        subscribers=150_000,
        views_per_day=150_000.0,
        subscriber_multiplier=45.0,
        is_exceptional=True,
    )

    analysis = SimpleNamespace(
        collection=SimpleNamespace(
            niche="AI productivity",
            saved_count=3,
        ),
        results=SimpleNamespace(
            considered_count=3,
            videos=(
                regular,
                breakout,
                exceptional,
            ),
        ),
    )

    report = build_analysis_report(analysis)

    assert "Breakout highlights: 1" in report
    assert "Exceptional-performance highlights: 1" in report
    assert "250,000" in report
    assert "50.00x" in report
    assert "[BREAKOUT]" in report
    assert "[EXCEPTIONAL PERFORMANCE]" in report
    assert (
        report.index("1. Regular high-view video")
        < report.index("2. Small-channel breakout")
        < report.index("3. Large-channel exceptional video")
    )
