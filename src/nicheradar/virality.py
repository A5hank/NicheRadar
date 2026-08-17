"""Calculate transparent niche virality and confidence scores."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite, log10
from statistics import median


class ViralityLabel(StrEnum):
    """Human-readable category for a Virality Score."""

    LOW_ACTIVITY = "low_activity"
    EMERGING = "emerging"
    ACTIVE = "active"
    STRONG = "strong"
    HIGHLY_VIRAL = "highly_viral"


class ConfidenceLabel(StrEnum):
    """Human-readable category for a Confidence Score."""

    LOW = "low"
    MODERATE = "moderate"
    GOOD = "good"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class ViralityScore:
    """Complete Virality Score and its component values."""

    score: int
    label: ViralityLabel
    breakout_points: int
    velocity_points: int
    exceptional_points: int
    diversity_points: int
    median_views_per_day: float
    video_count: int
    breakout_count: int
    exceptional_count: int
    unique_channel_count: int


@dataclass(frozen=True, slots=True)
class ConfidenceScore:
    """Complete Confidence Score and its supporting values."""

    score: int
    label: ConfidenceLabel
    query_points: int
    candidate_points: int
    result_points: int
    subscriber_points: int
    query_count: int
    videos_considered: int
    videos_returned: int
    videos_with_subscriber_data: int
    subscriber_completeness_percent: float


def calculate_breakout_points(
    breakout_count: int,
) -> int:
    """Award breakout points using the approved count tiers."""

    if breakout_count < 0:
        raise ValueError(
            "breakout_count must not be negative"
        )

    if breakout_count <= 1:
        return 0

    if breakout_count <= 3:
        return 10

    if breakout_count <= 8:
        return 20

    if breakout_count <= 14:
        return 30

    return 40


def calculate_velocity_points(
    median_views_per_day: float,
) -> int:
    """Convert median view velocity into zero to thirty points."""

    if (
        not isfinite(median_views_per_day)
        or median_views_per_day < 0
    ):
        raise ValueError(
            "median_views_per_day must be a finite "
            "non-negative number"
        )

    if median_views_per_day <= 1_000:
        return 0

    if median_views_per_day >= 100_000:
        return 30

    velocity_position = (
        log10(median_views_per_day / 1_000)
        / log10(100_000 / 1_000)
    )

    return round(velocity_position * 30)


def calculate_exceptional_points(
    *,
    exceptional_count: int,
    video_count: int,
) -> int:
    """Award up to fifteen points from the exceptional rate."""

    if exceptional_count < 0:
        raise ValueError(
            "exceptional_count must not be negative"
        )

    if video_count < 0:
        raise ValueError(
            "video_count must not be negative"
        )

    if exceptional_count > video_count:
        raise ValueError(
            "exceptional_count cannot exceed video_count"
        )

    if video_count == 0:
        return 0

    exceptional_rate = (
        exceptional_count / video_count
    )

    normalized_rate = min(
        exceptional_rate / 0.10,
        1.0,
    )

    return round(normalized_rate * 15)


def calculate_diversity_points(
    unique_channel_count: int,
) -> int:
    """Award creator-diversity points using channel tiers."""

    if unique_channel_count < 0:
        raise ValueError(
            "unique_channel_count must not be negative"
        )

    if unique_channel_count < 10:
        return 0

    if unique_channel_count < 20:
        return 4

    if unique_channel_count < 30:
        return 8

    if unique_channel_count < 40:
        return 12

    return 15


def determine_virality_label(
    score: int,
) -> ViralityLabel:
    """Convert a numerical Virality Score into its label."""

    if not 0 <= score <= 100:
        raise ValueError(
            "Virality Score must be between 0 and 100"
        )

    if score <= 24:
        return ViralityLabel.LOW_ACTIVITY

    if score <= 49:
        return ViralityLabel.EMERGING

    if score <= 69:
        return ViralityLabel.ACTIVE

    if score <= 84:
        return ViralityLabel.STRONG

    return ViralityLabel.HIGHLY_VIRAL


def calculate_virality_score(
    *,
    views_per_day: Iterable[int | float],
    breakout_count: int,
    exceptional_count: int,
    unique_channel_count: int,
) -> ViralityScore:
    """Calculate a complete Virality Score from ranked videos."""

    velocity_values = tuple(
        float(value)
        for value in views_per_day
    )

    for value in velocity_values:
        if not isfinite(value) or value < 0:
            raise ValueError(
                "views_per_day values must be finite "
                "and non-negative"
            )

    video_count = len(velocity_values)

    if breakout_count < 0:
        raise ValueError(
            "breakout_count must not be negative"
        )

    if exceptional_count < 0:
        raise ValueError(
            "exceptional_count must not be negative"
        )

    if breakout_count + exceptional_count > video_count:
        raise ValueError(
            "highlight counts cannot exceed video_count"
        )

    if not 0 <= unique_channel_count <= video_count:
        raise ValueError(
            "unique_channel_count must be between "
            "zero and video_count"
        )

    if video_count == 0:
        median_velocity = 0.0
    else:
        median_velocity = float(
            median(velocity_values)
        )

    breakout_points = calculate_breakout_points(
        breakout_count
    )

    velocity_points = calculate_velocity_points(
        median_velocity
    )

    exceptional_points = calculate_exceptional_points(
        exceptional_count=exceptional_count,
        video_count=video_count,
    )

    diversity_points = calculate_diversity_points(
        unique_channel_count
    )

    score = (
        breakout_points
        + velocity_points
        + exceptional_points
        + diversity_points
    )

    return ViralityScore(
        score=score,
        label=determine_virality_label(score),
        breakout_points=breakout_points,
        velocity_points=velocity_points,
        exceptional_points=exceptional_points,
        diversity_points=diversity_points,
        median_views_per_day=median_velocity,
        video_count=video_count,
        breakout_count=breakout_count,
        exceptional_count=exceptional_count,
        unique_channel_count=unique_channel_count,
    )


def calculate_candidate_points(
    videos_considered: int,
) -> int:
    """Award confidence points from the candidate-pool size."""

    if videos_considered < 0:
        raise ValueError(
            "videos_considered must not be negative"
        )

    if videos_considered == 0:
        return 0

    if videos_considered <= 30:
        return 5

    if videos_considered <= 60:
        return 10

    if videos_considered <= 90:
        return 15

    if videos_considered <= 120:
        return 20

    return 25


def calculate_result_points(
    videos_returned: int,
) -> int:
    """Award confidence points from the ranked result count."""

    if videos_returned < 0:
        raise ValueError(
            "videos_returned must not be negative"
        )

    if videos_returned == 0:
        return 0

    if videos_returned <= 10:
        return 5

    if videos_returned <= 20:
        return 10

    if videos_returned <= 30:
        return 15

    if videos_returned <= 40:
        return 20

    return 25


def calculate_subscriber_points(
    *,
    videos_with_subscriber_data: int,
    videos_returned: int,
) -> tuple[int, float]:
    """Award confidence points from subscriber-data completeness."""

    if videos_with_subscriber_data < 0:
        raise ValueError(
            "videos_with_subscriber_data must not be negative"
        )

    if videos_returned < 0:
        raise ValueError(
            "videos_returned must not be negative"
        )

    if videos_with_subscriber_data > videos_returned:
        raise ValueError(
            "videos_with_subscriber_data cannot exceed "
            "videos_returned"
        )

    if videos_returned == 0:
        return 0, 0.0

    completeness_ratio = (
        videos_with_subscriber_data
        / videos_returned
    )

    completeness_percent = (
        completeness_ratio * 100
    )

    if videos_with_subscriber_data == 0:
        points = 0
    elif completeness_ratio <= 0.20:
        points = 6
    elif completeness_ratio <= 0.40:
        points = 12
    elif completeness_ratio <= 0.60:
        points = 18
    elif completeness_ratio <= 0.80:
        points = 24
    else:
        points = 30

    return points, completeness_percent


def determine_confidence_label(
    score: int,
) -> ConfidenceLabel:
    """Convert a numerical Confidence Score into its label."""

    if not 0 <= score <= 100:
        raise ValueError(
            "Confidence Score must be between 0 and 100"
        )

    if score <= 39:
        return ConfidenceLabel.LOW

    if score <= 69:
        return ConfidenceLabel.MODERATE

    if score <= 84:
        return ConfidenceLabel.GOOD

    return ConfidenceLabel.HIGH


def calculate_confidence_score(
    *,
    query_count: int,
    videos_considered: int,
    videos_returned: int,
    videos_with_subscriber_data: int,
) -> ConfidenceScore:
    """Calculate how reliable the Virality Score is."""

    if not 1 <= query_count <= 5:
        raise ValueError(
            "query_count must be between 1 and 5"
        )

    if videos_considered < 0:
        raise ValueError(
            "videos_considered must not be negative"
        )

    if videos_returned < 0:
        raise ValueError(
            "videos_returned must not be negative"
        )

    if videos_considered < videos_returned:
        raise ValueError(
            "videos_considered cannot be smaller "
            "than videos_returned"
        )

    subscriber_points, completeness_percent = (
        calculate_subscriber_points(
            videos_with_subscriber_data=(
                videos_with_subscriber_data
            ),
            videos_returned=videos_returned,
        )
    )

    if videos_returned == 0:
        return ConfidenceScore(
            score=0,
            label=ConfidenceLabel.LOW,
            query_points=0,
            candidate_points=0,
            result_points=0,
            subscriber_points=0,
            query_count=query_count,
            videos_considered=videos_considered,
            videos_returned=0,
            videos_with_subscriber_data=0,
            subscriber_completeness_percent=0.0,
        )

    query_points = query_count * 4

    candidate_points = calculate_candidate_points(
        videos_considered
    )

    result_points = calculate_result_points(
        videos_returned
    )

    score = (
        query_points
        + candidate_points
        + result_points
        + subscriber_points
    )

    return ConfidenceScore(
        score=score,
        label=determine_confidence_label(score),
        query_points=query_points,
        candidate_points=candidate_points,
        result_points=result_points,
        subscriber_points=subscriber_points,
        query_count=query_count,
        videos_considered=videos_considered,
        videos_returned=videos_returned,
        videos_with_subscriber_data=(
            videos_with_subscriber_data
        ),
        subscriber_completeness_percent=(
            completeness_percent
        ),
    )