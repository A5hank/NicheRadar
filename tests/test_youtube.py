"""Tests for the YouTube Data API client."""

from datetime import UTC, datetime

import httpx
import pytest

from nicheradar.youtube import (
    YouTubeAPIError,
    YouTubeClient,
    YouTubeMetadataError,
    format_rfc3339_utc,
    parse_iso8601_duration,
    select_thumbnail_url,
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


def test_thumbnail_selector_prefers_medium_size() -> None:
    """Medium thumbnails should be preferred for dashboard cards."""

    thumbnails = {
        "default": {
            "url": "https://images.example/default.jpg",
        },
        "medium": {
            "url": "  https://images.example/medium.jpg  ",
        },
        "high": {
            "url": "https://images.example/high.jpg",
        },
    }

    thumbnail_url = select_thumbnail_url(thumbnails)

    assert thumbnail_url == "https://images.example/medium.jpg"


def test_thumbnail_selector_uses_next_valid_size() -> None:
    """Malformed preferred thumbnails should not prevent a fallback."""

    thumbnails = {
        "medium": {
            "url": "   ",
        },
        "high": {
            "url": "https://images.example/high.jpg",
        },
        "default": {
            "url": "https://images.example/default.jpg",
        },
    }

    thumbnail_url = select_thumbnail_url(thumbnails)

    assert thumbnail_url == "https://images.example/high.jpg"


@pytest.mark.parametrize(
    "thumbnails",
    [
        None,
        [],
        {},
        {
            "medium": None,
        },
        {
            "medium": {
                "url": "   ",
            }
        },
    ],
)
def test_thumbnail_selector_handles_missing_metadata(
    thumbnails: object,
) -> None:
    """Missing thumbnail metadata should produce no thumbnail URL."""

    assert select_thumbnail_url(thumbnails) is None


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


@pytest.mark.parametrize(
    ("duration", "expected_seconds"),
    [
        ("PT58S", 58),
        ("PT1M12S", 72),
        ("PT2H3M4S", 7_384),
        ("P1DT2H", 93_600),
    ],
)
def test_parse_iso8601_duration(
    duration: str,
    expected_seconds: int,
) -> None:
    """ISO 8601 durations should become total seconds."""

    assert parse_iso8601_duration(duration) == expected_seconds


def test_invalid_duration_is_rejected() -> None:
    """Malformed YouTube durations should be rejected."""

    with pytest.raises(
        YouTubeMetadataError,
        match="Invalid YouTube duration",
    ):
        parse_iso8601_duration("one minute")


def test_fetches_video_and_channel_details() -> None:
    """The client should fetch and parse public metadata."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        if request.url.path.endswith("/videos"):
            assert request.url.params["part"] == "snippet,contentDetails,statistics"
            assert request.url.params["id"] == "video-123"

            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "video-123",
                            "snippet": {
                                "title": ("AI &amp; Automation"),
                                "channelId": "channel-123",
                                "channelTitle": ("Practical AI"),
                                "publishedAt": ("2026-08-13T12:00:00Z"),
                                "tags": [
                                    "AI",
                                    "automation",
                                ],
                                "thumbnails": {
                                    "default": {
                                        "url": ("https://images.example/video-123-default.jpg"),
                                    },
                                    "medium": {
                                        "url": ("https://images.example/video-123-medium.jpg"),
                                    },
                                    "high": {
                                        "url": ("https://images.example/video-123-high.jpg"),
                                    },
                                },
                            },
                            "contentDetails": {
                                "duration": "PT1M12S",
                            },
                            "statistics": {
                                "viewCount": "800000",
                                "likeCount": "42000",
                                "commentCount": "1200",
                            },
                        }
                    ]
                },
            )

        if request.url.path.endswith("/channels"):
            assert request.url.params["part"] == "snippet,statistics"
            assert request.url.params["id"] == "channel-123"

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

    transport = httpx.MockTransport(handler)

    with YouTubeClient(
        "test-api-key",
        transport=transport,
    ) as client:
        videos = client.fetch_video_details(["video-123"])
        channels = client.fetch_channel_details(["channel-123"])

    video = videos[0]
    channel = channels[0]

    assert video.title == "AI & Automation"
    assert video.duration_seconds == 72
    assert video.view_count == 800_000
    assert video.like_count == 42_000
    assert video.comment_count == 1_200
    assert video.tags == ("AI", "automation")
    assert video.thumbnail_url == ("https://images.example/video-123-medium.jpg")
    assert video.is_short_candidate is True

    assert channel.channel_title == "Practical AI"
    assert channel.subscriber_count == 5_000
    assert channel.video_count == 120
    assert channel.hidden_subscriber_count is False


def test_hidden_subscriber_count_becomes_none() -> None:
    """Hidden subscriber counts must not be treated as zero."""

    def handler(
        _request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "hidden-channel",
                        "snippet": {
                            "title": "Private Creator",
                        },
                        "statistics": {
                            "videoCount": "25",
                            "hiddenSubscriberCount": True,
                        },
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)

    with YouTubeClient(
        "test-api-key",
        transport=transport,
    ) as client:
        channels = client.fetch_channel_details(["hidden-channel"])

    assert channels[0].subscriber_count is None
    assert channels[0].hidden_subscriber_count is True
