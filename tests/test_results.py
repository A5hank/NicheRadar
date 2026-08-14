"""Tests for final NicheRadar result selection."""

from datetime import UTC, datetime

import pytest

from nicheradar.analytics import (
    PerformanceLabel,
    PerformanceMetrics,
)
from nicheradar.ranking import ScoredVideo
from nicheradar.results import build_niche_results

UPLOAD_DATE = datetime(
    2026,
    8,
    14,
    12,
    0,
    tzinfo=UTC,
)


def make_scored_video(
    *,
    video_id: str,
    label: PerformanceLabel,
    views_per_day: float,
    multiplier: float,
    views: int,
) -> ScoredVideo:
    """Create a scored video for result-selection tests."""

    metrics = PerformanceMetrics(
        age_hours=24.0,
        views_per_hour=views_per_day / 24,
        views_per_day=views_per_day,
        like_rate=0.05,
        comment_rate=0.001,
        engagement_rate=0.051,
        subscriber_multiplier=multiplier,
        performance_label=label,
    )

    return ScoredVideo(
        video_id=video_id,
        title=f"Video {video_id}",
        url=(f"https://www.youtube.com/watch?v={video_id}"),
        channel_id=f"channel-{video_id}",
        channel_name=f"Channel {video_id}",
        upload_date=UPLOAD_DATE,
        views=views,
        subscribers=1_000,
        metrics=metrics,
    )


def test_selects_by_views_then_ranks_by_views_per_day() -> None:
    """Selection and display ranking should use different metrics."""

    highest_views = make_scored_video(
        video_id="highest-views",
        label=PerformanceLabel.REGULAR,
        views_per_day=100_000,
        multiplier=10.0,
        views=500_000,
    )
    second_highest_views = make_scored_video(
        video_id="second-highest-views",
        label=PerformanceLabel.REGULAR,
        views_per_day=250_000,
        multiplier=10.0,
        views=400_000,
    )
    third_highest_views = make_scored_video(
        video_id="third-highest-views",
        label=PerformanceLabel.REGULAR,
        views_per_day=150_000,
        multiplier=10.0,
        views=300_000,
    )
    low_view_breakout = make_scored_video(
        video_id="low-view-breakout",
        label=PerformanceLabel.BREAKOUT,
        views_per_day=1_000_000,
        multiplier=100.0,
        views=50_000,
    )

    results = build_niche_results(
        [
            low_view_breakout,
            third_highest_views,
            highest_views,
            second_highest_views,
        ],
        limit=3,
    )

    assert [video.video_id for video in results.videos] == [
        "second-highest-views",
        "third-highest-views",
        "highest-views",
    ]

    assert results.total_count == 3
    assert results.breakout_count == 0


def test_selected_special_video_keeps_its_label() -> None:
    """Labels should highlight selected videos without selecting them."""

    exceptional = make_scored_video(
        video_id="exceptional",
        label=(PerformanceLabel.EXCEPTIONAL_PERFORMANCE),
        views_per_day=70_000,
        multiplier=45.0,
        views=600_000,
    )
    regular = make_scored_video(
        video_id="regular",
        label=PerformanceLabel.REGULAR,
        views_per_day=100_000,
        multiplier=10.0,
        views=500_000,
    )
    excluded_breakout = make_scored_video(
        video_id="excluded-breakout",
        label=PerformanceLabel.BREAKOUT,
        views_per_day=500_000,
        multiplier=100.0,
        views=50_000,
    )

    results = build_niche_results(
        [
            excluded_breakout,
            regular,
            exceptional,
        ],
        limit=2,
    )

    assert [video.video_id for video in results.videos] == [
        "regular",
        "exceptional",
    ]

    assert results.breakout_count == 0
    assert results.exceptional_performance_count == 1


def test_duplicate_keeps_highest_view_observation() -> None:
    """Duplicate IDs should retain the copy with more views."""

    higher_view_copy = make_scored_video(
        video_id="same-video",
        label=PerformanceLabel.REGULAR,
        views_per_day=50_000,
        multiplier=10.0,
        views=100_000,
    )
    faster_but_lower_view_copy = make_scored_video(
        video_id="same-video",
        label=PerformanceLabel.REGULAR,
        views_per_day=500_000,
        multiplier=10.0,
        views=50_000,
    )

    results = build_niche_results(
        [
            faster_but_lower_view_copy,
            higher_view_copy,
        ]
    )

    assert results.considered_count == 1
    assert results.total_count == 1
    assert results.videos[0].views == 100_000
    assert results.videos[0].metrics.views_per_day == pytest.approx(50_000)


def test_empty_input_produces_empty_results() -> None:
    """No scored videos should produce empty results."""

    results = build_niche_results([])

    assert results.considered_count == 0
    assert results.videos == ()
    assert results.all_videos == ()
    assert results.total_count == 0
    assert results.breakout_count == 0
    assert results.exceptional_performance_count == 0


def test_result_builder_rejects_invalid_limit() -> None:
    """The result limit must be positive."""

    with pytest.raises(
        ValueError,
        match="limit must be at least 1",
    ):
        build_niche_results(
            [],
            limit=0,
        )
