"""Regression coverage for isolation between same-niche analysis runs."""

from datetime import UTC, datetime, timedelta

from nicheradar.database import (
    create_database_engine,
    create_database_schema,
    create_session_factory,
)
from nicheradar.repositories import (
    create_analysis_run,
    get_analysis_videos_by_run,
    save_analysis_video,
)


def test_same_niche_runs_return_only_their_own_videos() -> None:
    """Two same-day runs must not mix videos when queried for a report."""

    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    collected_at = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)

    try:
        create_database_schema(engine)
        session_factory = create_session_factory(engine)

        with session_factory.begin() as session:
            first_run = create_analysis_run(
                session,
                niche="Minecraft",
                query_fingerprint="a" * 64,
                approved_queries=("Minecraft",),
                collected_at=collected_at,
                expires_at=collected_at + timedelta(days=30),
            )
            second_run = create_analysis_run(
                session,
                niche="Minecraft",
                query_fingerprint="b" * 64,
                approved_queries=("Minecraft shorts",),
                collected_at=collected_at,
                expires_at=collected_at + timedelta(days=30),
            )

            for run, video_id in ((first_run, "first-video"), (second_run, "second-video")):
                save_analysis_video(
                    session,
                    analysis_run_id=run.id,
                    video_id=video_id,
                    title=video_id,
                    url=f"https://youtube.com/watch?v={video_id}",
                    thumbnail_url=None,
                    channel_id="channel-123",
                    channel_name="Minecraft Channel",
                    views=100_000,
                    likes=5_000,
                    comments=100,
                    subscribers=4_000,
                    duration_seconds=45,
                    upload_date=collected_at - timedelta(days=1),
                )

        with session_factory() as session:
            assert [
                video.video_id
                for video in get_analysis_videos_by_run(session, analysis_run_id=first_run.id)
            ] == ["first-video"]
            assert [
                video.video_id
                for video in get_analysis_videos_by_run(session, analysis_run_id=second_run.id)
            ] == ["second-video"]
    finally:
        engine.dispose()
