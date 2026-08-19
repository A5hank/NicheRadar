"""Tests for niche Virality and Confidence Scores."""

import pytest

from nicheradar.virality import (
    ConfidenceLabel,
    ViralityLabel,
    calculate_breakout_points,
    calculate_candidate_points,
    calculate_confidence_score,
    calculate_diversity_points,
    calculate_exceptional_points,
    calculate_result_points,
    calculate_subscriber_points,
    calculate_velocity_points,
    calculate_virality_score,
)


@pytest.mark.parametrize(
    ("breakout_count", "expected_points"),
    [
        (0, 0),
        (1, 0),
        (2, 10),
        (3, 10),
        (4, 20),
        (8, 20),
        (9, 30),
        (14, 30),
        (15, 40),
        (50, 40),
    ],
)
def test_breakout_point_tiers(
    breakout_count: int,
    expected_points: int,
) -> None:
    """Every breakout boundary should award its approved points."""

    assert calculate_breakout_points(breakout_count) == expected_points


@pytest.mark.parametrize(
    ("median_velocity", "expected_points"),
    [
        (0, 0),
        (1_000, 0),
        (10_000, 15),
        (100_000, 30),
        (1_000_000, 30),
    ],
)
def test_velocity_point_boundaries(
    median_velocity: float,
    expected_points: int,
) -> None:
    """Velocity should use logarithmic scaling and remain capped."""

    assert calculate_velocity_points(median_velocity) == expected_points


def test_exceptional_points_use_returned_video_rate() -> None:
    """Five exceptional videos out of fifty should earn full points."""

    assert (
        calculate_exceptional_points(
            exceptional_count=1,
            video_count=50,
        )
        == 3
    )

    assert (
        calculate_exceptional_points(
            exceptional_count=5,
            video_count=50,
        )
        == 15
    )

    assert (
        calculate_exceptional_points(
            exceptional_count=20,
            video_count=50,
        )
        == 15
    )


@pytest.mark.parametrize(
    ("unique_channels", "expected_points"),
    [
        (0, 0),
        (9, 0),
        (10, 4),
        (19, 4),
        (20, 8),
        (29, 8),
        (30, 12),
        (39, 12),
        (40, 15),
        (50, 15),
    ],
)
def test_creator_diversity_tiers(
    unique_channels: int,
    expected_points: int,
) -> None:
    """Unique-channel boundaries should award their tier points."""

    assert calculate_diversity_points(unique_channels) == expected_points


def test_calculates_complete_virality_score() -> None:
    """The agreed example should produce a strong score of 79."""

    result = calculate_virality_score(
        views_per_day=[41_200] * 50,
        breakout_count=15,
        exceptional_count=1,
        unique_channel_count=34,
    )

    assert result.score == 79
    assert result.label is ViralityLabel.STRONG
    assert result.breakout_points == 40
    assert result.velocity_points == 24
    assert result.exceptional_points == 3
    assert result.diversity_points == 12
    assert result.median_views_per_day == 41_200


@pytest.mark.parametrize(
    ("videos_considered", "expected_points"),
    [
        (0, 0),
        (1, 5),
        (30, 5),
        (31, 10),
        (60, 10),
        (61, 15),
        (90, 15),
        (91, 20),
        (120, 20),
        (121, 25),
        (400, 25),
    ],
)
def test_candidate_coverage_tiers(
    videos_considered: int,
    expected_points: int,
) -> None:
    """Candidate coverage should use ranges rather than exact values."""

    assert calculate_candidate_points(videos_considered) == expected_points


@pytest.mark.parametrize(
    ("videos_returned", "expected_points"),
    [
        (0, 0),
        (1, 5),
        (10, 5),
        (11, 10),
        (20, 10),
        (21, 15),
        (30, 15),
        (31, 20),
        (40, 20),
        (41, 25),
        (50, 25),
    ],
)
def test_ranked_result_tiers(
    videos_returned: int,
    expected_points: int,
) -> None:
    """Ranked sample depth should use the approved ranges."""

    assert calculate_result_points(videos_returned) == expected_points


@pytest.mark.parametrize(
    (
        "known_subscriber_counts",
        "expected_points",
    ),
    [
        (0, 0),
        (1, 6),
        (10, 6),
        (11, 12),
        (20, 12),
        (21, 18),
        (30, 18),
        (31, 24),
        (40, 24),
        (41, 30),
        (50, 30),
    ],
)
def test_subscriber_completeness_tiers(
    known_subscriber_counts: int,
    expected_points: int,
) -> None:
    """Subscriber completeness should use percentage ranges."""

    points, percentage = calculate_subscriber_points(
        videos_with_subscriber_data=(known_subscriber_counts),
        videos_returned=50,
    )

    assert points == expected_points
    assert percentage == pytest.approx(known_subscriber_counts / 50 * 100)


def test_calculates_complete_confidence_score() -> None:
    """The agreed mockup inputs should produce 94 confidence."""

    result = calculate_confidence_score(
        query_count=10,
        videos_considered=400,
        videos_returned=50,
        videos_with_subscriber_data=40,
    )

    assert result.score == 94
    assert result.label is ConfidenceLabel.HIGH
    assert result.query_points == 20
    assert result.candidate_points == 25
    assert result.result_points == 25
    assert result.subscriber_points == 24
    assert result.subscriber_completeness_percent == pytest.approx(80)


@pytest.mark.parametrize(
    ("query_count", "expected_points"),
    [
        (1, 2),
        (5, 10),
        (10, 20),
    ],
)
def test_confidence_query_points_scale_with_query_coverage(
    query_count: int,
    expected_points: int,
) -> None:
    """Query confidence should scale to a maximum of 20 points."""

    result = calculate_confidence_score(
        query_count=query_count,
        videos_considered=400,
        videos_returned=50,
        videos_with_subscriber_data=40,
    )

    assert result.query_points == expected_points


@pytest.mark.parametrize(
    "query_count",
    [
        0,
        11,
    ],
)
def test_confidence_rejects_unsupported_query_counts(
    query_count: int,
) -> None:
    """Confidence should reject query counts outside the supported range."""

    with pytest.raises(
        ValueError,
        match="query_count must be between 1 and 10",
    ):
        calculate_confidence_score(
            query_count=query_count,
            videos_considered=400,
            videos_returned=50,
            videos_with_subscriber_data=40,
        )


def test_no_results_force_confidence_to_zero() -> None:
    """No returned videos means no reliable Virality Score."""

    result = calculate_confidence_score(
        query_count=5,
        videos_considered=100,
        videos_returned=0,
        videos_with_subscriber_data=0,
    )

    assert result.score == 0
    assert result.label is ConfidenceLabel.LOW
    assert result.query_points == 0
    assert result.candidate_points == 0
    assert result.result_points == 0
    assert result.subscriber_points == 0


def test_rejects_impossible_subscriber_count() -> None:
    """Known subscriber data cannot exceed returned videos."""

    with pytest.raises(
        ValueError,
        match="cannot exceed",
    ):
        calculate_confidence_score(
            query_count=5,
            videos_considered=50,
            videos_returned=50,
            videos_with_subscriber_data=51,
        )
