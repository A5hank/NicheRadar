"""Tests for NicheRadar ORM models and constraints."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from nicheradar.database import (
    create_database_engine,
    create_database_schema,
    create_session_factory,
)
from nicheradar.models import Channel, Snapshot, Video


def make_video(
    *,
    channel_id: str,
    niche: str = "AI productivity",
    collected_date: date = date(2026, 8, 12),
) -> Video:
    """Create a valid Video object for testing."""

    return Video(
        video_id="video-123",
        title="Build an AI workflow in 60 seconds",
        url="https://youtube.com/shorts/video-123",
        channel_id=channel_id,
        views=800_000,
        likes=42_000,
        comments=1_200,
        subscribers=5_000,
        duration_seconds=58,
        upload_date=datetime(
            2026,
            8,
            11,
            12,
            0,
            tzinfo=UTC,
        ),
        niche=niche,
        collected_date=collected_date,
    )


def test_schema_creates_all_tables() -> None:
    """Schema creation should produce all three NicheRadar tables."""

    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
    )

    try:
        create_database_schema(engine)

        table_names = set(inspect(engine).get_table_names())

        assert table_names == {
            "channels",
            "snapshots",
            "videos",
        }
    finally:
        engine.dispose()


def test_models_store_data_and_relationships() -> None:
    """ORM models should persist data and expose relationships."""

    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
    )

    try:
        create_database_schema(engine)
        session_factory = create_session_factory(engine)

        channel = Channel(
            channel_id="channel-123",
            channel_name="Practical AI",
            subscriber_count=5_000,
        )
        video = make_video(
            channel_id=channel.channel_id,
        )
        video.thumbnail_url = (
            "https://images.example/video-123-medium.jpg"
        )
        snapshot = Snapshot(
            niche="AI productivity",
            snapshot_date=date(2026, 8, 12),
            video_count=50,
            average_views=300_000,
            median_views=180_000,
        )

        video.channel = channel

        with session_factory() as session:
            session.add_all(
                [
                    channel,
                    video,
                    snapshot,
                ]
            )
            session.commit()

            stored_video = session.scalar(
                select(Video).where(
                    Video.video_id == "video-123",
                )
            )

            assert stored_video is not None
            assert stored_video.views == 800_000
            assert stored_video.thumbnail_url == (
                "https://images.example/video-123-medium.jpg"
            )
            assert stored_video.channel.channel_name == "Practical AI"
            assert stored_video in channel.videos
    finally:
        engine.dispose()


def test_foreign_key_rejects_unknown_channel() -> None:
    """A video cannot reference a channel that does not exist."""

    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
    )

    try:
        create_database_schema(engine)
        session_factory = create_session_factory(engine)

        with session_factory() as session:
            session.add(
                make_video(
                    channel_id="missing-channel",
                )
            )

            with pytest.raises(IntegrityError):
                session.commit()

            session.rollback()
    finally:
        engine.dispose()


def test_duplicate_daily_video_observation_is_rejected() -> None:
    """The same video, niche, and collection date must be unique."""

    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
    )

    try:
        create_database_schema(engine)
        session_factory = create_session_factory(engine)

        channel = Channel(
            channel_id="channel-123",
            channel_name="Practical AI",
            subscriber_count=5_000,
        )

        first_video = make_video(
            channel_id=channel.channel_id,
        )
        duplicate_video = make_video(
            channel_id=channel.channel_id,
        )

        with session_factory() as session:
            session.add_all(
                [
                    channel,
                    first_video,
                    duplicate_video,
                ]
            )

            with pytest.raises(IntegrityError):
                session.commit()

            session.rollback()
    finally:
        engine.dispose()
