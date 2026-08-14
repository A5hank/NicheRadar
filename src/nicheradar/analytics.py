"""Pure performance analytics for NicheRadar videos."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

SECONDS_PER_HOUR = 3_600
HOURS_PER_DAY = 24
MINIMUM_VELOCITY_AGE_HOURS = 1.0

MICRO_CHANNEL_MAXIMUM_SUBSCRIBERS = 500
SMALL_CHANNEL_MAXIMUM_SUBSCRIBERS = 999
BREAKOUT_MAXIMUM_SUBSCRIBERS = 100_000

SMALL_CHANNEL_MULTIPLIER_THRESHOLD = 40.0
GROWTH_CHANNEL_MULTIPLIER_THRESHOLD = 20.0
EXCEPTIONAL_MULTIPLIER_THRESHOLD = 40.0

MICRO_CHANNEL_VIEW_THRESHOLD = 50_000
SMALL_CHANNEL_VIEW_THRESHOLD = 100_000


class PerformanceLabel(StrEnum):
    """Classification assigned to a video's performance."""

    REGULAR = "regular"
    BREAKOUT = "breakout"
    EXCEPTIONAL_PERFORMANCE = "exceptional_performance"


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    """Calculated performance metrics for one video."""

    age_hours: float
    views_per_hour: float
    views_per_day: float
    like_rate: float | None
    comment_rate: float | None
    engagement_rate: float | None
    subscriber_multiplier: float | None
    performance_label: PerformanceLabel

    @property
    def is_breakout(self) -> bool:
        """Return whether the video is classified as a breakout."""

        return self.performance_label is PerformanceLabel.BREAKOUT

    @property
    def is_exceptional_performance(self) -> bool:
        """Return whether a large channel performed exceptionally."""

        return self.performance_label is PerformanceLabel.EXCEPTIONAL_PERFORMANCE


def validate_non_negative(
    name: str,
    value: int | None,
) -> None:
    """Reject negative analytics inputs."""

    if value is not None and value < 0:
        raise ValueError(f"{name} must not be negative")


def calculate_rate(
    numerator: int | None,
    denominator: int,
) -> float | None:
    """Calculate a ratio when both values are usable."""

    validate_non_negative("numerator", numerator)
    validate_non_negative("denominator", denominator)

    if numerator is None or denominator == 0:
        return None

    return numerator / denominator


def calculate_subscriber_multiplier(
    *,
    views: int,
    subscribers: int | None,
) -> float | None:
    """Calculate how many views a video has per subscriber."""

    validate_non_negative("views", views)
    validate_non_negative("subscribers", subscribers)

    if subscribers is None or subscribers == 0:
        return None

    return views / subscribers


def classify_performance(
    *,
    views: int,
    subscribers: int | None,
) -> PerformanceLabel:
    """Classify performance using channel-size-specific rules."""

    multiplier = calculate_subscriber_multiplier(
        views=views,
        subscribers=subscribers,
    )

    if subscribers is None or subscribers == 0 or multiplier is None:
        return PerformanceLabel.REGULAR

    if subscribers <= MICRO_CHANNEL_MAXIMUM_SUBSCRIBERS:
        if multiplier > SMALL_CHANNEL_MULTIPLIER_THRESHOLD and views > MICRO_CHANNEL_VIEW_THRESHOLD:
            return PerformanceLabel.BREAKOUT

        return PerformanceLabel.REGULAR

    if subscribers <= SMALL_CHANNEL_MAXIMUM_SUBSCRIBERS:
        if multiplier > SMALL_CHANNEL_MULTIPLIER_THRESHOLD and views > SMALL_CHANNEL_VIEW_THRESHOLD:
            return PerformanceLabel.BREAKOUT

        return PerformanceLabel.REGULAR

    if subscribers <= BREAKOUT_MAXIMUM_SUBSCRIBERS:
        if multiplier > GROWTH_CHANNEL_MULTIPLIER_THRESHOLD:
            return PerformanceLabel.BREAKOUT

        return PerformanceLabel.REGULAR

    if multiplier > EXCEPTIONAL_MULTIPLIER_THRESHOLD:
        return PerformanceLabel.EXCEPTIONAL_PERFORMANCE

    return PerformanceLabel.REGULAR


def qualifies_as_breakout(
    *,
    views: int,
    subscribers: int | None,
) -> bool:
    """Return whether a video receives the breakout label."""

    return (
        classify_performance(
            views=views,
            subscribers=subscribers,
        )
        is PerformanceLabel.BREAKOUT
    )


def qualifies_as_exceptional_performance(
    *,
    views: int,
    subscribers: int | None,
) -> bool:
    """Return whether a large-channel video is exceptional."""

    return (
        classify_performance(
            views=views,
            subscribers=subscribers,
        )
        is PerformanceLabel.EXCEPTIONAL_PERFORMANCE
    )


def normalize_stored_datetime(
    value: datetime,
) -> datetime:
    """Return a database datetime as timezone-aware UTC."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def calculate_performance_metrics(
    *,
    views: int,
    likes: int | None,
    comments: int | None,
    subscribers: int | None,
    upload_date: datetime,
    as_of: datetime,
) -> PerformanceMetrics:
    """Calculate all performance metrics for one video."""

    validate_non_negative("views", views)
    validate_non_negative("likes", likes)
    validate_non_negative("comments", comments)
    validate_non_negative("subscribers", subscribers)

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")

    normalized_upload_date = normalize_stored_datetime(upload_date)
    normalized_as_of = as_of.astimezone(UTC)

    age_seconds = (normalized_as_of - normalized_upload_date).total_seconds()

    if age_seconds < 0:
        raise ValueError("upload_date must not be after as_of")

    age_hours = age_seconds / SECONDS_PER_HOUR

    velocity_age_hours = max(
        age_hours,
        MINIMUM_VELOCITY_AGE_HOURS,
    )

    views_per_hour = views / velocity_age_hours
    views_per_day = views_per_hour * HOURS_PER_DAY

    like_rate = calculate_rate(
        likes,
        views,
    )
    comment_rate = calculate_rate(
        comments,
        views,
    )

    engagement_rate = None

    if likes is not None and comments is not None:
        engagement_rate = calculate_rate(
            likes + comments,
            views,
        )

    subscriber_multiplier = calculate_subscriber_multiplier(
        views=views,
        subscribers=subscribers,
    )

    performance_label = classify_performance(
        views=views,
        subscribers=subscribers,
    )

    return PerformanceMetrics(
        age_hours=age_hours,
        views_per_hour=views_per_hour,
        views_per_day=views_per_day,
        like_rate=like_rate,
        comment_rate=comment_rate,
        engagement_rate=engagement_rate,
        subscriber_multiplier=subscriber_multiplier,
        performance_label=performance_label,
    )
