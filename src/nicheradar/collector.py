"""YouTube niche collection workflow."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import mean, median

from sqlalchemy.orm import Session

from nicheradar.repositories import (
    create_analysis_run,
    save_analysis_snapshot,
    save_analysis_video,
)
from nicheradar.youtube import YouTubeClient

SEARCH_WINDOW_DAYS = 7


@dataclass(frozen=True, slots=True)
class CollectionSummary:
    """Summary of one completed niche collection."""

    analysis_run_id: str
    niche: str
    search_queries: tuple[str, ...]
    searched_count: int
    unique_video_count: int
    fetched_count: int
    short_candidate_count: int
    saved_count: int
    skipped_count: int


def _prepare_search_queries(
    *,
    niche: str,
    search_queries: Sequence[str] | None,
) -> tuple[str, ...]:
    """Return clean, unique queries with the niche first."""

    prepared_queries = [niche]
    seen_queries = {niche.casefold()}

    if search_queries is None:
        return tuple(prepared_queries)

    if isinstance(search_queries, str):
        raise TypeError("search_queries must be a sequence of strings, not one string")

    for search_query in search_queries:
        if not isinstance(search_query, str):
            raise TypeError("search_queries must contain only strings")

        cleaned_query = " ".join(search_query.split())

        if not cleaned_query:
            continue

        comparison_key = cleaned_query.casefold()

        if comparison_key in seen_queries:
            continue

        prepared_queries.append(cleaned_query)
        seen_queries.add(comparison_key)

    return tuple(prepared_queries)


def collect_niche(
    *,
    client: YouTubeClient,
    session: Session,
    niche: str,
    search_queries: Sequence[str] | None = None,
    collected_at: datetime | None = None,
    query_fingerprint: str = "local",
    expires_at: datetime | None = None,
    max_results: int = 50,
) -> CollectionSummary:
    """Collect recent YouTube data and stage it for storage."""

    cleaned_niche = niche.strip()

    if not cleaned_niche:
        raise ValueError("niche must not be empty")

    prepared_search_queries = _prepare_search_queries(
        niche=cleaned_niche,
        search_queries=search_queries,
    )

    current_time = collected_at or datetime.now(UTC)

    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("collected_at must be timezone-aware")

    current_time = current_time.astimezone(UTC)
    published_after = current_time - timedelta(days=SEARCH_WINDOW_DAYS)
    retention_deadline = expires_at or (current_time + timedelta(days=30))

    if retention_deadline.tzinfo is None or retention_deadline.utcoffset() is None:
        raise ValueError("expires_at must be timezone-aware")

    searched_count = 0
    video_ids: list[str] = []
    seen_video_ids: set[str] = set()

    for search_query in prepared_search_queries:
        query_video_ids = client.search_video_ids(
            query=search_query,
            published_after=published_after,
            max_results=max_results,
        )

        searched_count += len(query_video_ids)

        for video_id in query_video_ids:
            if video_id in seen_video_ids:
                continue

            video_ids.append(video_id)
            seen_video_ids.add(video_id)

    videos = client.fetch_video_details(video_ids)

    short_candidates = [video for video in videos if video.is_short_candidate]

    channel_ids = list(dict.fromkeys(video.channel_id for video in short_candidates))

    channels = client.fetch_channel_details(channel_ids)
    channels_by_id = {channel.channel_id: channel for channel in channels}

    valid_pairs = []

    for video in short_candidates:
        channel = channels_by_id.get(video.channel_id)

        if channel is None or video.view_count is None:
            continue

        valid_pairs.append((video, channel))

    analysis_run = create_analysis_run(
        session,
        niche=cleaned_niche,
        query_fingerprint=query_fingerprint,
        approved_queries=prepared_search_queries,
        collected_at=current_time,
        expires_at=retention_deadline.astimezone(UTC),
    )

    saved_views: list[int] = []

    for video, channel in valid_pairs:
        save_analysis_video(
            session,
            analysis_run_id=analysis_run.id,
            video_id=video.video_id,
            title=video.title,
            url=video.url,
            thumbnail_url=video.thumbnail_url,
            channel_id=video.channel_id,
            channel_name=channel.channel_title,
            views=video.view_count,
            likes=video.like_count,
            comments=video.comment_count,
            subscribers=channel.subscriber_count,
            duration_seconds=video.duration_seconds,
            tags=video.tags,
            upload_date=video.published_at,
        )

        saved_views.append(video.view_count)

    if saved_views:
        save_analysis_snapshot(
            session,
            analysis_run_id=analysis_run.id,
            video_count=len(saved_views),
            average_views=float(mean(saved_views)),
            median_views=float(median(saved_views)),
        )

    return CollectionSummary(
        analysis_run_id=analysis_run.id,
        niche=cleaned_niche,
        search_queries=prepared_search_queries,
        searched_count=searched_count,
        unique_video_count=len(video_ids),
        fetched_count=len(videos),
        short_candidate_count=len(short_candidates),
        saved_count=len(saved_views),
        skipped_count=len(videos) - len(saved_views),
    )
