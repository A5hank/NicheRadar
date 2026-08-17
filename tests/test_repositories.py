"""Tests for NicheRadar repository operations."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select

from nicheradar.database import (
    create_database_engine,
    create_database_schema,
    create_session_factory,
)
from nicheradar.models import Channel, Snapshot, Video
from nicheradar.repositories import (
    get_videos_by_niche,
    upsert_channel,
    upsert_snapshot,
    upsert_video_observation,
)

COLLECTION_DATE = date(2026, 8, 14)
UPLOAD_DATE = datetime(
    2026,
    8,
    13,
    12,
    0,
    tzinfo=UTC,
)


def save_sample_video(
    session,
    *,
    video_id: str = "video-123",
    views: int = 800_000,
    thumbnail_url: str | None = None,
) -> tuple[Video, bool]:
    """Save a reusable video observation for repository tests."""

    return upsert_video_observation(
        session,
        video_id=video_id,
        title="Build an AI workflow in 60 seconds",
        url=f"https://youtube.com/shorts/{video_id}",
        thumbnail_url=thumbnail_url,
        channel_id="channel-123",
        views=views,
        likes=42_000,
        comments=1_200,
        subscribers=5_000,
        duration_seconds=58,
        upload_date=UPLOAD_DATE,
        niche="AI productivity",
        collected_date=COLLECTION_DATE,
    )


def test_repository_transaction_stores_collection() -> None:
    """A successful transaction should store all collection records."""

    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
    )

    try:
        create_database_schema(engine)
        session_factory = create_session_factory(engine)

        with session_factory.begin() as session:
            channel, channel_created = upsert_channel(
                session,
                channel_id="channel-123",
                channel_name="Practical AI",
                subscriber_count=5_000,
            )
            video, video_created = save_sample_video(session)
            snapshot, snapshot_created = upsert_snapshot(
                session,
                niche="AI productivity",
                snapshot_date=COLLECTION_DATE,
                video_count=1,
                average_views=800_000,
                median_views=800_000,
            )

            assert channel_created is True
            assert video_created is True
            assert snapshot_created is True
            assert video.channel_id == channel.channel_id
            assert snapshot.video_count == 1

        with session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Channel)) == 1
            assert session.scalar(select(func.count()).select_from(Video)) == 1
            assert session.scalar(select(func.count()).select_from(Snapshot)) == 1
    finally:
        engine.dispose()


def test_upserts_update_instead_of_duplicate() -> None:
    """Repeated collection should update the existing daily rows."""

    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
    )

    try:
        create_database_schema(engine)
        session_factory = create_session_factory(engine)

        with session_factory.begin() as session:
            upsert_channel(
                session,
                channel_id="channel-123",
                channel_name="Practical AI",
                subscriber_count=5_000,
            )
            save_sample_video(
                session,
                views=800_000,
                thumbnail_url=(
                    "https://images.example/"
                    "video-123-original.jpg"
                ),
            )

        with session_factory.begin() as session:
            channel, channel_created = upsert_channel(
                session,
                channel_id="channel-123",
                channel_name="Practical AI Updated",
                subscriber_count=5_500,
            )
            video, video_created = save_sample_video(
                session,
                views=900_000,
                thumbnail_url=(
                    "https://images.example/"
                    "video-123-updated.jpg"
                ),
            )

            assert channel_created is False
            assert video_created is False
            assert channel.subscriber_count == 5_500
            assert video.views == 900_000
            assert video.thumbnail_url == (
                "https://images.example/"
                "video-123-updated.jpg"
            )

        with session_factory() as session:
            video_count = session.scalar(
                select(func.count()).select_from(Video)
            )
            stored_video = session.scalar(select(Video))

            assert video_count == 1
            assert stored_video is not None
            assert stored_video.views == 900_000
            assert stored_video.thumbnail_url == (
                "https://images.example/"
                "video-123-updated.jpg"
            )
    finally:
        engine.dispose()


def test_get_videos_by_niche_orders_by_views() -> None:
    """Niche results should place the most-viewed video first."""

    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
    )

    try:
        create_database_schema(engine)
        session_factory = create_session_factory(engine)

        with session_factory.begin() as session:
            upsert_channel(
                session,
                channel_id="channel-123",
                channel_name="Practical AI",
                subscriber_count=5_000,
            )
            save_sample_video(
                session,
                video_id="lower-view-video",
                views=100_000,
            )
            save_sample_video(
                session,
                video_id="higher-view-video",
                views=900_000,
            )

        with session_factory() as session:
            videos = get_videos_by_niche(
                session,
                niche="AI productivity",
                collected_date=COLLECTION_DATE,
                limit=50,
            )

            assert [video.video_id for video in videos] == [
                "higher-view-video",
                "lower-view-video",
            ]
    finally:
        engine.dispose()


def test_failed_transaction_rolls_back_everything() -> None:
    """An error should prevent partial collection data from being saved."""

    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
    )

    try:
        create_database_schema(engine)
        session_factory = create_session_factory(engine)

        with pytest.raises(RuntimeError):
            with session_factory.begin() as session:
                upsert_channel(
                    session,
                    channel_id="channel-123",
                    channel_name="Practical AI",
                    subscriber_count=5_000,
                )
                save_sample_video(session)

                raise RuntimeError("Simulated collection failure")

        with session_factory() as session:
            channel_count = session.scalar(select(func.count()).select_from(Channel))
            video_count = session.scalar(select(func.count()).select_from(Video))

            assert channel_count == 0
            assert video_count == 0
    finally:
        engine.dispose()
