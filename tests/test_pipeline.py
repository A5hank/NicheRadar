"""Tests for the complete NicheRadar analysis pipeline."""

from datetime import UTC, datetime

import httpx
from sqlalchemy import select

from nicheradar.analytics import PerformanceLabel
from nicheradar.database import (
    create_database_engine,
    create_database_schema,
    create_session_factory,
)
from nicheradar.models import Video
from nicheradar.pipeline import run_niche_analysis
from nicheradar.youtube import YouTubeClient

ANALYSIS_TIME = datetime(
    2026,
    8,
    14,
    12,
    0,
    tzinfo=UTC,
)


def test_pipeline_collects_scores_and_selects_videos() -> None:
    """The pipeline should complete every analysis stage."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        if request.url.path.endswith("/search"):
            assert request.url.params["q"] == "AI productivity"

            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": {
                                "videoId": "video-123",
                            }
                        }
                    ]
                },
            )

        if request.url.path.endswith("/videos"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "video-123",
                            "snippet": {
                                "title": "AI Workflow Short",
                                "channelId": "channel-123",
                                "channelTitle": "Practical AI",
                                "publishedAt": ("2026-08-13T12:00:00Z"),
                                "tags": [
                                    "AI",
                                    "productivity",
                                ],
                            },
                            "contentDetails": {
                                "duration": "PT58S",
                            },
                            "statistics": {
                                "viewCount": "250000",
                                "likeCount": "10000",
                                "commentCount": "500",
                            },
                        }
                    ]
                },
            )

        if request.url.path.endswith("/channels"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "channel-123",
                            "snippet": {
                                "title": "Practical AI",
                            },
                            "statistics": {
                                "subscriberCount": "5000",
                                "videoCount": "120",
                                "hiddenSubscriberCount": False,
                            },
                        }
                    ]
                },
            )

        raise AssertionError(f"Unexpected endpoint: {request.url.path}")

    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    transport = httpx.MockTransport(handler)

    try:
        create_database_schema(engine)
        session_factory = create_session_factory(engine)

        with YouTubeClient(
            "test-api-key",
            transport=transport,
        ) as client:
            with session_factory.begin() as session:
                analysis = run_niche_analysis(
                    client=client,
                    session=session,
                    niche="AI productivity",
                    analyzed_at=ANALYSIS_TIME,
                )

        assert analysis.collection.saved_count == 1
        assert analysis.results.considered_count == 1
        assert analysis.results.total_count == 1

        video = analysis.results.videos[0]

        assert video.video_id == "video-123"
        assert video.views == 250_000
        assert video.metrics.views_per_day == 250_000
        assert video.metrics.subscriber_multiplier == 50.0
        assert video.metrics.performance_label is PerformanceLabel.BREAKOUT

        with session_factory() as session:
            stored_video = session.scalar(select(Video).where(Video.video_id == "video-123"))

            assert stored_video is not None
            assert stored_video.views == 250_000
    finally:
        engine.dispose()
