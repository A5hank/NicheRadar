"""Score and rank stored NicheRadar video observations."""

from dataclasses import dataclass
from datetime import datetime

from nicheradar.analytics import (
    PerformanceMetrics,
    calculate_performance_metrics,
)
from nicheradar.models import Video


@dataclass(frozen=True, slots=True)
class ScoredVideo:
    """A stored video combined with calculated analytics."""

    video_id: str
    title: str
    url: str
    channel_id: str
    channel_name: str
    upload_date: datetime
    views: int
    subscribers: int | None
    metrics: PerformanceMetrics


def score_video(
    video: Video,
    *,
    as_of: datetime,
) -> ScoredVideo:
    """Calculate analytics for one stored video."""

    if video.channel is None:
        raise ValueError(f"Video {video.video_id} has no channel.")

    metrics = calculate_performance_metrics(
        views=video.views,
        likes=video.likes,
        comments=video.comments,
        subscribers=video.subscribers,
        upload_date=video.upload_date,
        as_of=as_of,
    )

    return ScoredVideo(
        video_id=video.video_id,
        title=video.title,
        url=video.url,
        channel_id=video.channel_id,
        channel_name=video.channel.channel_name,
        upload_date=video.upload_date,
        views=video.views,
        subscribers=video.subscribers,
        metrics=metrics,
    )


def scored_video_velocity_sort_key(
    video: ScoredVideo,
) -> tuple[float, int, str]:
    """Build a deterministic view-velocity sorting key."""

    return (
        -video.metrics.views_per_day,
        -video.views,
        video.video_id,
    )


def rank_scored_videos(
    videos: list[ScoredVideo],
) -> list[ScoredVideo]:
    """Return scored videos ordered by view velocity."""

    return sorted(
        videos,
        key=scored_video_velocity_sort_key,
    )


def rank_videos(
    videos: list[Video],
    *,
    as_of: datetime,
    limit: int | None = 50,
) -> list[ScoredVideo]:
    """Score stored videos and rank them by view velocity."""

    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1")

    scored_videos = [
        score_video(
            video,
            as_of=as_of,
        )
        for video in videos
    ]

    ranked_videos = rank_scored_videos(scored_videos)

    if limit is None:
        return ranked_videos

    return ranked_videos[:limit]
