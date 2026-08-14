"""Tests for the YouTube Data API client."""

from datetime import UTC, datetime

import httpx
import pytest

from nicheradar.youtube import (
    YouTubeAPIError,
    YouTubeClient,
    format_rfc3339_utc,
)


def test_format_rfc3339_utc() -> None:
    """Datetime values should be converted to RFC 3339 UTC."""

    value = datetime(
        2026,
        8,
        7,
        16,
        0,
        tzinfo=UTC,
    )

    assert format_rfc3339_utc(value) == "2026-08-07T16:00:00Z"


def test_rfc3339_rejects_naive_datetime() -> None:
    """A datetime without timezone information is ambiguous."""

    value = datetime(2026, 8, 7, 16, 0)

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        format_rfc3339_utc(value)


def test_search_returns_video_ids() -> None:
    """Search should send correct parameters and extract IDs."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.path.endswith("/search")
        assert request.url.params["part"] == "snippet"
        assert request.url.params["type"] == "video"
        assert request.url.params["q"] == "AI productivity"
        assert request.url.params["order"] == "viewCount"
        assert request.url.params["videoDuration"] == "short"
        assert request.url.params["maxResults"] == "50"
        assert request.url.params["publishedAfter"] == "2026-08-07T10:30:00Z"
        assert request.url.params["key"] == "test-api-key"

        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": {
                            "kind": "youtube#video",
                            "videoId": "video-123",
                        }
                    },
                    {
                        "id": {
                            "kind": "youtube#video",
                            "videoId": "video-456",
                        }
                    },
                ]
            },
        )

    transport = httpx.MockTransport(handler)

    with YouTubeClient(
        "test-api-key",
        transport=transport,
    ) as client:
        video_ids = client.search_video_ids(
            query="AI productivity",
            published_after=datetime(
                2026,
                8,
                7,
                10,
                30,
                tzinfo=UTC,
            ),
        )

    assert video_ids == [
        "video-123",
        "video-456",
    ]


def test_search_rejects_invalid_result_limit() -> None:
    """YouTube search allows at most 50 results per request."""

    with YouTubeClient("test-api-key") as client:
        with pytest.raises(
            ValueError,
            match="between 1 and 50",
        ):
            client.search_video_ids(
                query="AI productivity",
                published_after=datetime.now(UTC),
                max_results=51,
            )


def test_api_error_does_not_expose_key() -> None:
    """Error messages must not contain the YouTube API key."""

    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "error": {
                    "message": "API key not valid.",
                }
            },
        )

    transport = httpx.MockTransport(handler)

    with YouTubeClient(
        "super-secret-key",
        transport=transport,
    ) as client:
        with pytest.raises(
            YouTubeAPIError,
        ) as error_info:
            client.search_video_ids(
                query="AI productivity",
                published_after=datetime.now(UTC),
            )

    message = str(error_info.value)

    assert "API key not valid" in message
    assert "super-secret-key" not in message
