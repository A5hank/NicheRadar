"""Tests for NicheRadar performance analytics."""

from datetime import UTC, datetime

import pytest

from nicheradar.analytics import (
    PerformanceLabel,
    calculate_performance_metrics,
    calculate_subscriber_multiplier,
    classify_performance,
    qualifies_as_breakout,
    qualifies_as_exceptional_performance,
)

UPLOAD_DATE = datetime(
    2026,
    8,
    13,
    12,
    0,
    tzinfo=UTC,
)
ANALYSIS_TIME = datetime(
    2026,
    8,
    14,
    12,
    0,
    tzinfo=UTC,
)


def test_calculates_complete_performance_metrics() -> None:
    """All metrics should be calculated from valid data."""

    metrics = calculate_performance_metrics(
        views=250_000,
        likes=10_000,
        comments=500,
        subscribers=5_000,
        upload_date=UPLOAD_DATE,
        as_of=ANALYSIS_TIME,
    )

    assert metrics.age_hours == pytest.approx(24.0)
    assert metrics.views_per_hour == pytest.approx(10_416.6667)
    assert metrics.views_per_day == pytest.approx(250_000)
    assert metrics.like_rate == pytest.approx(0.04)
    assert metrics.comment_rate == pytest.approx(0.002)
    assert metrics.engagement_rate == pytest.approx(0.042)
    assert metrics.subscriber_multiplier == pytest.approx(50.0)
    assert metrics.performance_label is PerformanceLabel.BREAKOUT
    assert metrics.is_breakout is True
    assert metrics.is_exceptional_performance is False


@pytest.mark.parametrize(
    (
        "views",
        "subscribers",
        "expected_label",
    ),
    [
        (
            50_001,
            500,
            PerformanceLabel.BREAKOUT,
        ),
        (
            50_000,
            500,
            PerformanceLabel.REGULAR,
        ),
        (
            100_001,
            501,
            PerformanceLabel.BREAKOUT,
        ),
        (
            100_000,
            501,
            PerformanceLabel.REGULAR,
        ),
        (
            20_001,
            1_000,
            PerformanceLabel.BREAKOUT,
        ),
        (
            20_000,
            1_000,
            PerformanceLabel.REGULAR,
        ),
        (
            2_000_001,
            100_000,
            PerformanceLabel.BREAKOUT,
        ),
        (
            4_000_041,
            100_001,
            PerformanceLabel.EXCEPTIONAL_PERFORMANCE,
        ),
        (
            4_000_040,
            100_001,
            PerformanceLabel.REGULAR,
        ),
        (
            3_000_030,
            100_001,
            PerformanceLabel.REGULAR,
        ),
        (
            500_000,
            None,
            PerformanceLabel.REGULAR,
        ),
        (
            500_000,
            0,
            PerformanceLabel.REGULAR,
        ),
    ],
)
def test_performance_classification_boundaries(
    views: int,
    subscribers: int | None,
    expected_label: PerformanceLabel,
) -> None:
    """Classification should follow exact range boundaries."""

    result = classify_performance(
        views=views,
        subscribers=subscribers,
    )

    assert result is expected_label


def test_large_channel_is_not_called_breakout() -> None:
    """Large-channel exceptional results must use a new label."""

    views = 4_100_000
    subscribers = 100_001

    assert (
        qualifies_as_breakout(
            views=views,
            subscribers=subscribers,
        )
        is False
    )
    assert (
        qualifies_as_exceptional_performance(
            views=views,
            subscribers=subscribers,
        )
        is True
    )


def test_hidden_subscribers_produce_no_multiplier() -> None:
    """Hidden subscribers should not produce a multiplier."""

    multiplier = calculate_subscriber_multiplier(
        views=500_000,
        subscribers=None,
    )

    assert multiplier is None


def test_missing_engagement_values_remain_unknown() -> None:
    """Unavailable likes and comments should remain None."""

    metrics = calculate_performance_metrics(
        views=50_000,
        likes=None,
        comments=None,
        subscribers=2_000,
        upload_date=UPLOAD_DATE,
        as_of=ANALYSIS_TIME,
    )

    assert metrics.like_rate is None
    assert metrics.comment_rate is None
    assert metrics.engagement_rate is None
    assert metrics.subscriber_multiplier == pytest.approx(25.0)
    assert metrics.is_breakout is True


def test_velocity_uses_minimum_one_hour_window() -> None:
    """Very new videos should use a stable one-hour denominator."""

    upload_date = datetime(
        2026,
        8,
        14,
        11,
        30,
        tzinfo=UTC,
    )

    metrics = calculate_performance_metrics(
        views=2_400,
        likes=100,
        comments=10,
        subscribers=1_000,
        upload_date=upload_date,
        as_of=ANALYSIS_TIME,
    )

    assert metrics.age_hours == pytest.approx(0.5)
    assert metrics.views_per_hour == pytest.approx(2_400)
    assert metrics.views_per_day == pytest.approx(57_600)


def test_naive_stored_upload_date_is_treated_as_utc() -> None:
    """SQLite timestamps without timezone should remain usable."""

    naive_upload_date = datetime(
        2026,
        8,
        13,
        12,
        0,
    )

    metrics = calculate_performance_metrics(
        views=100_000,
        likes=5_000,
        comments=100,
        subscribers=5_000,
        upload_date=naive_upload_date,
        as_of=ANALYSIS_TIME,
    )

    assert metrics.age_hours == pytest.approx(24.0)


def test_future_upload_date_is_rejected() -> None:
    """Upload dates after the analysis time are invalid."""

    future_upload_date = datetime(
        2026,
        8,
        15,
        12,
        0,
        tzinfo=UTC,
    )

    with pytest.raises(
        ValueError,
        match="upload_date must not be after as_of",
    ):
        calculate_performance_metrics(
            views=100,
            likes=10,
            comments=1,
            subscribers=50,
            upload_date=future_upload_date,
            as_of=ANALYSIS_TIME,
        )


def test_negative_statistics_are_rejected() -> None:
    """Impossible negative statistics should fail validation."""

    with pytest.raises(
        ValueError,
        match="views must not be negative",
    ):
        calculate_performance_metrics(
            views=-1,
            likes=10,
            comments=1,
            subscribers=50,
            upload_date=UPLOAD_DATE,
            as_of=ANALYSIS_TIME,
        )
