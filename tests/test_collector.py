"""Tests for the complete YouTube collection workflow."""

from datetime import UTC, datetime

import httpx
from sqlalchemy import select

from nicheradar.collector import collect_niche
from nicheradar.database import (
    create_database_engine,
    create_database_schema,
    create_session_factory,
)
from nicheradar.models import Channel, Snapshot, Video
from nicheradar.youtube import YouTubeClient


def test_collection_saves_valid_short_candidates() -> None:
    """Collection should search, deduplicate, and save API data."""

    searched_queries: list[str] = []

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        if request.url.path.endswith("/search"):
            query = request.url.params["q"]
            searched_queries.append(query)

            if query == "AI productivity":
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": {
                                    "videoId": "short-video",
                                }
                            },
                            {
                                "id": {
                                    "videoId": "long-video",
                                }
                            },
                        ]
                    },
                )

            if query == "AI tools":
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": {
                                    "videoId": "short-video",
                                }
                            }
                        ]
                    },
                )

            raise AssertionError(f"Unexpected search query: {query}")

        if request.url.path.endswith("/videos"):
            requested_video_ids = request.url.params["id"].split(",")

            assert requested_video_ids == [
                "short-video",
                "long-video",
            ]

            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "short-video",
                            "snippet": {
                                "title": "AI Short",
                                "channelId": "channel-123",
                                "channelTitle": "Practical AI",
                                "publishedAt": ("2026-08-13T12:00:00Z"),
                                "thumbnails": {
                                    "medium": {
                                        "url": (
                                            "https://images.example/"
                                            "short-video-medium.jpg"
                                        ),
                                    },
                                },
                                "tags": [
                                    "AI",
                                    "productivity",
                                ],
                            },
                            "contentDetails": {
                                "duration": "PT58S",
                            },
                            "statistics": {
                                "viewCount": "800000",
                                "likeCount": "42000",
                                "commentCount": "1200",
                            },
                        },
                        {
                            "id": "long-video",
                            "snippet": {
                                "title": "Long AI Video",
                                "channelId": "channel-456",
                                "channelTitle": "Long Videos",
                                "publishedAt": ("2026-08-13T10:00:00Z"),
                            },
                            "contentDetails": {
                                "duration": "PT3M20S",
                            },
                            "statistics": {
                                "viewCount": "900000",
                            },
                        },
                    ]
                },
            )

        if request.url.path.endswith("/channels"):
            assert request.url.params["id"] == ("channel-123")

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
                summary = collect_niche(
                    client=client,
                    session=session,
                    niche="AI productivity",
                    search_queries=(
                        "AI productivity",
                        " AI tools ",
                        "ai productivity",
                    ),
                    collected_at=datetime(
                        2026,
                        8,
                        14,
                        12,
                        0,
                        tzinfo=UTC,
                    ),
                )

        with session_factory() as session:
            stored_video = session.scalar(select(Video))
            stored_channel = session.scalar(select(Channel))
            stored_snapshot = session.scalar(select(Snapshot))

            assert stored_video is not None
            assert stored_video.video_id == "short-video"
            assert stored_video.views == 800_000
            assert stored_video.subscribers == 5_000
            assert stored_video.tags == [
                "AI",
                "productivity",
            ]
            assert stored_video.thumbnail_url == (
                "https://images.example/"
                "short-video-medium.jpg"
            )

            assert stored_channel is not None
            assert stored_channel.video_count == 120

            assert stored_snapshot is not None
            assert stored_snapshot.video_count == 1
            assert stored_snapshot.average_views == 800_000

        assert searched_queries == [
            "AI productivity",
            "AI tools",
        ]
        assert summary.niche == "AI productivity"
        assert summary.search_queries == (
            "AI productivity",
            "AI tools",
        )
        assert summary.searched_count == 3
        assert summary.unique_video_count == 2
        assert summary.fetched_count == 2
        assert summary.short_candidate_count == 1
        assert summary.saved_count == 1
        assert summary.skipped_count == 1
    finally:
        engine.dispose()
