"""YouTube niche collection workflow."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import mean, median

from sqlalchemy.orm import Session

from nicheradar.repositories import (
    upsert_channel,
    upsert_snapshot,
    upsert_video_observation,
)
from nicheradar.youtube import YouTubeClient

SEARCH_WINDOW_DAYS = 7


@dataclass(frozen=True, slots=True)
class CollectionSummary:
    """Summary of one completed niche collection."""

    niche: str
    searched_count: int
    fetched_count: int
    short_candidate_count: int
    saved_count: int
    skipped_count: int


def collect_niche(
    *,
    client: YouTubeClient,
    session: Session,
    niche: str,
    collected_at: datetime | None = None,
    max_results: int = 50,
) -> CollectionSummary:
    """Collect recent YouTube data and stage it for storage."""

    cleaned_niche = niche.strip()

    if not cleaned_niche:
        raise ValueError("niche must not be empty")

    current_time = collected_at or datetime.now(UTC)

    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("collected_at must be timezone-aware")

    current_time = current_time.astimezone(UTC)
    collection_date = current_time.date()
    published_after = current_time - timedelta(days=SEARCH_WINDOW_DAYS)

    video_ids = client.search_video_ids(
        query=cleaned_niche,
        published_after=published_after,
        max_results=max_results,
    )

    videos = client.fetch_video_details(video_ids)

    short_candidates = [video for video in videos if video.is_short_candidate]

    channel_ids = [video.channel_id for video in short_candidates]

    channels = client.fetch_channel_details(channel_ids)
    channels_by_id = {channel.channel_id: channel for channel in channels}

    valid_pairs = []

    for video in short_candidates:
        channel = channels_by_id.get(video.channel_id)

        if channel is None or video.view_count is None:
            continue

        valid_pairs.append((video, channel))

    used_channel_ids = {video.channel_id for video, _channel in valid_pairs}

    for channel_id in used_channel_ids:
        channel = channels_by_id[channel_id]

        upsert_channel(
            session,
            channel_id=channel.channel_id,
            channel_name=channel.channel_title,
            subscriber_count=channel.subscriber_count,
            video_count=channel.video_count,
        )

    saved_views: list[int] = []

    for video, channel in valid_pairs:
        upsert_video_observation(
            session,
            video_id=video.video_id,
            title=video.title,
            url=video.url,
            channel_id=video.channel_id,
            views=video.view_count,
            likes=video.like_count,
            comments=video.comment_count,
            subscribers=channel.subscriber_count,
            duration_seconds=video.duration_seconds,
            tags=video.tags,
            upload_date=video.published_at,
            niche=cleaned_niche,
            collected_date=collection_date,
        )

        saved_views.append(video.view_count)

    if saved_views:
        upsert_snapshot(
            session,
            niche=cleaned_niche,
            snapshot_date=collection_date,
            video_count=len(saved_views),
            average_views=float(mean(saved_views)),
            median_views=float(median(saved_views)),
        )

    return CollectionSummary(
        niche=cleaned_niche,
        searched_count=len(video_ids),
        fetched_count=len(videos),
        short_candidate_count=len(short_candidates),
        saved_count=len(saved_views),
        skipped_count=len(videos) - len(saved_views),
    )
