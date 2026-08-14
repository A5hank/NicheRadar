"""Tests for scoring and ranking stored videos."""

from datetime import UTC, date, datetime

import pytest

from nicheradar.analytics import PerformanceLabel
from nicheradar.models import Channel, Video
from nicheradar.ranking import rank_videos, score_video

ANALYSIS_TIME = datetime(
    2026,
    8,
    14,
    12,
    0,
    tzinfo=UTC,
)


def make_video(
    *,
    video_id: str,
    views: int,
    subscribers: int,
    upload_date: datetime,
    channel_id: str = "channel-123",
) -> Video:
    """Create a valid video and channel for ranking tests."""

    channel = Channel(
        channel_id=channel_id,
        channel_name=f"Channel {channel_id}",
        subscriber_count=subscribers,
        video_count=100,
    )

    video = Video(
        video_id=video_id,
        title=f"Video {video_id}",
        url=(f"https://www.youtube.com/watch?v={video_id}"),
        channel_id=channel_id,
        views=views,
        likes=1_000,
        comments=100,
        subscribers=subscribers,
        duration_seconds=60,
        tags=["test"],
        upload_date=upload_date,
        niche="AI productivity",
        collected_date=date(2026, 8, 14),
    )

    video.channel = channel

    return video


def test_score_video_combines_storage_and_analytics() -> None:
    """A scored video should contain data and calculated metrics."""

    video = make_video(
        video_id="video-123",
        views=250_000,
        subscribers=5_000,
        upload_date=datetime(
            2026,
            8,
            13,
            12,
            0,
            tzinfo=UTC,
        ),
    )

    scored_video = score_video(
        video,
        as_of=ANALYSIS_TIME,
    )

    assert scored_video.video_id == "video-123"
    assert scored_video.channel_name == ("Channel channel-123")
    assert scored_video.views == 250_000
    assert scored_video.metrics.views_per_day == (pytest.approx(250_000))
    assert scored_video.metrics.performance_label is PerformanceLabel.BREAKOUT


def test_ranking_uses_views_per_day_before_total_views() -> None:
    """A faster new video should outrank a slower older video."""

    older_video = make_video(
        video_id="older-video",
        views=100_000,
        subscribers=10_000,
        upload_date=datetime(
            2026,
            8,
            12,
            12,
            0,
            tzinfo=UTC,
        ),
        channel_id="older-channel",
    )
    newer_video = make_video(
        video_id="newer-video",
        views=60_000,
        subscribers=10_000,
        upload_date=datetime(
            2026,
            8,
            13,
            12,
            0,
            tzinfo=UTC,
        ),
        channel_id="newer-channel",
    )

    ranked_videos = rank_videos(
        [
            older_video,
            newer_video,
        ],
        as_of=ANALYSIS_TIME,
    )

    assert [video.video_id for video in ranked_videos] == [
        "newer-video",
        "older-video",
    ]

    assert ranked_videos[0].metrics.views_per_day == (pytest.approx(60_000))
    assert ranked_videos[1].metrics.views_per_day == (pytest.approx(50_000))


def test_large_channel_receives_exceptional_label() -> None:
    """Large channels must not be labelled as breakouts."""

    video = make_video(
        video_id="large-channel-video",
        views=4_100_000,
        subscribers=100_001,
        upload_date=datetime(
            2026,
            8,
            13,
            12,
            0,
            tzinfo=UTC,
        ),
        channel_id="large-channel",
    )

    scored_video = score_video(
        video,
        as_of=ANALYSIS_TIME,
    )

    assert scored_video.metrics.is_breakout is False
    assert scored_video.metrics.is_exceptional_performance is True
    assert scored_video.metrics.performance_label is PerformanceLabel.EXCEPTIONAL_PERFORMANCE


def test_ranking_respects_limit() -> None:
    """The ranking should return no more than its limit."""

    videos = [
        make_video(
            video_id=f"video-{index}",
            views=100_000 + index,
            subscribers=10_000,
            upload_date=datetime(
                2026,
                8,
                13,
                12,
                0,
                tzinfo=UTC,
            ),
            channel_id=f"channel-{index}",
        )
        for index in range(5)
    ]

    ranked_videos = rank_videos(
        videos,
        as_of=ANALYSIS_TIME,
        limit=3,
    )

    assert len(ranked_videos) == 3


def test_ranking_rejects_invalid_limit() -> None:
    """A result limit must request at least one video."""

    with pytest.raises(
        ValueError,
        match="limit must be at least 1",
    ):
        rank_videos(
            [],
            as_of=ANALYSIS_TIME,
            limit=0,
        )
