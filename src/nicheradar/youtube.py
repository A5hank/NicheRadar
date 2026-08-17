"""Client utilities for the YouTube Data API."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from types import TracebackType
from typing import Any, Self

import httpx

YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3/"
DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_IDS_PER_REQUEST = 50
MAX_SHORT_DURATION_SECONDS = 180
THUMBNAIL_SIZE_PREFERENCE = (
    "medium",
    "high",
    "default",
)

_DURATION_PATTERN = re.compile(
    r"^P"
    r"(?:(?P<days>\d+)D)?"
    r"(?:T"
    r"(?:(?P<hours>\d+)H)?"
    r"(?:(?P<minutes>\d+)M)?"
    r"(?:(?P<seconds>\d+)S)?"
    r")?$"
)


class YouTubeAPIError(RuntimeError):
    """Raised when a YouTube Data API request fails."""


class YouTubeMetadataError(ValueError):
    """Raised when YouTube returns malformed metadata."""


@dataclass(frozen=True, slots=True)
class VideoDetails:
    """Public metadata for one YouTube video."""

    video_id: str
    title: str
    channel_id: str
    channel_title: str
    published_at: datetime
    view_count: int | None
    like_count: int | None
    comment_count: int | None
    duration_seconds: int
    tags: tuple[str, ...]
    thumbnail_url: str | None = None

    @property
    def is_short_candidate(self) -> bool:
        """Return whether the duration fits the Shorts limit."""

        return 0 < self.duration_seconds <= MAX_SHORT_DURATION_SECONDS

    @property
    def url(self) -> str:
        """Return the normal YouTube watch URL."""

        return f"https://www.youtube.com/watch?v={self.video_id}"


@dataclass(frozen=True, slots=True)
class ChannelDetails:
    """Public metadata for one YouTube channel."""

    channel_id: str
    channel_title: str
    subscriber_count: int | None
    video_count: int | None
    hidden_subscriber_count: bool


def format_rfc3339_utc(value: datetime) -> str:
    """Convert a timezone-aware datetime to RFC 3339 UTC."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("value must be timezone-aware")

    utc_value = value.astimezone(UTC)

    return utc_value.isoformat(
        timespec="seconds",
    ).replace("+00:00", "Z")


def parse_youtube_datetime(value: str) -> datetime:
    """Parse a YouTube RFC 3339 datetime into UTC."""

    normalized_value = value

    if value.endswith("Z"):
        normalized_value = f"{value[:-1]}+00:00"

    try:
        parsed_value = datetime.fromisoformat(normalized_value)
    except ValueError as error:
        raise YouTubeMetadataError(f"Invalid YouTube datetime: {value}") from error

    if parsed_value.tzinfo is None or parsed_value.utcoffset() is None:
        raise YouTubeMetadataError("YouTube datetime must include a timezone")

    return parsed_value.astimezone(UTC)


def parse_iso8601_duration(value: str) -> int:
    """Convert an ISO 8601 duration into total seconds."""

    match = _DURATION_PATTERN.fullmatch(value)

    if match is None:
        raise YouTubeMetadataError(f"Invalid YouTube duration: {value}")

    components = match.groupdict()

    if all(component is None for component in components.values()):
        raise YouTubeMetadataError(f"Invalid YouTube duration: {value}")

    days = int(components["days"] or 0)
    hours = int(components["hours"] or 0)
    minutes = int(components["minutes"] or 0)
    seconds = int(components["seconds"] or 0)

    return days * 86_400 + hours * 3_600 + minutes * 60 + seconds


def optional_int(value: Any) -> int | None:
    """Convert an API value to int when present and valid."""

    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def select_thumbnail_url(
    thumbnails: object,
) -> str | None:
    """Choose the most suitable available YouTube thumbnail URL."""

    if not isinstance(thumbnails, dict):
        return None

    for size_name in THUMBNAIL_SIZE_PREFERENCE:
        thumbnail = thumbnails.get(size_name)

        if not isinstance(thumbnail, dict):
            continue

        url = thumbnail.get("url")

        if not isinstance(url, str):
            continue

        cleaned_url = url.strip()

        if cleaned_url:
            return cleaned_url

    return None


def parse_video_resource(
    resource: dict[str, Any],
) -> VideoDetails:
    """Convert one raw YouTube video resource into typed data."""

    video_id = resource.get("id")
    snippet = resource.get("snippet")
    content_details = resource.get("contentDetails")
    statistics = resource.get("statistics")

    if not isinstance(video_id, str) or not video_id:
        raise YouTubeMetadataError("Video resource is missing its ID.")

    if not isinstance(snippet, dict):
        raise YouTubeMetadataError(f"Video {video_id} is missing its snippet.")

    if not isinstance(content_details, dict):
        raise YouTubeMetadataError(f"Video {video_id} is missing content details.")

    if not isinstance(statistics, dict):
        raise YouTubeMetadataError(f"Video {video_id} is missing statistics.")

    title = snippet.get("title")
    channel_id = snippet.get("channelId")
    channel_title = snippet.get("channelTitle")
    published_at = snippet.get("publishedAt")
    duration = content_details.get("duration")

    required_strings = {
        "title": title,
        "channelId": channel_id,
        "channelTitle": channel_title,
        "publishedAt": published_at,
        "duration": duration,
    }

    for field_name, field_value in required_strings.items():
        if not isinstance(field_value, str):
            raise YouTubeMetadataError(f"Video {video_id} has invalid {field_name}.")

    raw_tags = snippet.get("tags", [])
    tags: tuple[str, ...] = ()

    if isinstance(raw_tags, list):
        tags = tuple(unescape(tag) for tag in raw_tags if isinstance(tag, str))

    return VideoDetails(
        video_id=video_id,
        title=unescape(title),
        channel_id=channel_id,
        channel_title=unescape(channel_title),
        published_at=parse_youtube_datetime(published_at),
        view_count=optional_int(statistics.get("viewCount")),
        like_count=optional_int(statistics.get("likeCount")),
        comment_count=optional_int(statistics.get("commentCount")),
        duration_seconds=parse_iso8601_duration(duration),
        tags=tags,
        thumbnail_url=select_thumbnail_url(
            snippet.get("thumbnails"),
        ),
    )


def parse_channel_resource(
    resource: dict[str, Any],
) -> ChannelDetails:
    """Convert one raw YouTube channel resource into typed data."""

    channel_id = resource.get("id")
    snippet = resource.get("snippet")
    statistics = resource.get("statistics")

    if not isinstance(channel_id, str) or not channel_id:
        raise YouTubeMetadataError("Channel resource is missing its ID.")

    if not isinstance(snippet, dict):
        raise YouTubeMetadataError(f"Channel {channel_id} is missing its snippet.")

    if not isinstance(statistics, dict):
        raise YouTubeMetadataError(f"Channel {channel_id} is missing statistics.")

    channel_title = snippet.get("title")

    if not isinstance(channel_title, str):
        raise YouTubeMetadataError(f"Channel {channel_id} has an invalid title.")

    hidden_subscriber_count = statistics.get("hiddenSubscriberCount") is True

    subscriber_count = None

    if not hidden_subscriber_count:
        subscriber_count = optional_int(statistics.get("subscriberCount"))

    return ChannelDetails(
        channel_id=channel_id,
        channel_title=unescape(channel_title),
        subscriber_count=subscriber_count,
        video_count=optional_int(statistics.get("videoCount")),
        hidden_subscriber_count=hidden_subscriber_count,
    )


def unique_identifiers(
    identifiers: list[str],
) -> list[str]:
    """Remove empty and duplicate identifiers in original order."""

    unique_values: list[str] = []
    seen_values: set[str] = set()

    for identifier in identifiers:
        cleaned_identifier = identifier.strip()

        if cleaned_identifier and cleaned_identifier not in seen_values:
            unique_values.append(cleaned_identifier)
            seen_values.add(cleaned_identifier)

    return unique_values


class YouTubeClient:
    """Small synchronous client for public YouTube metadata."""

    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        cleaned_api_key = api_key.strip()

        if not cleaned_api_key:
            raise ValueError("api_key must not be empty")

        self._api_key = cleaned_api_key
        self._client = httpx.Client(
            base_url=YOUTUBE_API_BASE_URL,
            timeout=timeout_seconds,
            transport=transport,
        )

    def __enter__(self) -> Self:
        """Return this client when entering a context manager."""

        return self

    def __exit__(
        self,
        _exception_type: type[BaseException] | None,
        _exception: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        """Close resources when leaving a context manager."""

        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client."""

        self._client.close()

    def _get(
        self,
        endpoint: str,
        *,
        params: dict[str, str | int],
    ) -> dict[str, Any]:
        """Send one authenticated GET request to YouTube."""

        request_params = {
            **params,
            "key": self._api_key,
        }

        try:
            response = self._client.get(
                endpoint,
                params=request_params,
            )
        except httpx.RequestError:
            raise YouTubeAPIError("Unable to reach the YouTube Data API.") from None

        if response.is_error:
            try:
                payload = response.json()
                detail = payload["error"]["message"]
            except (KeyError, TypeError, ValueError):
                detail = "YouTube returned an unspecified error."

            raise YouTubeAPIError(
                f"YouTube API request failed with status {response.status_code}: {detail}"
            ) from None

        payload = response.json()

        if not isinstance(payload, dict):
            raise YouTubeAPIError("YouTube returned an unexpected response.")

        return payload

    def _fetch_resources(
        self,
        *,
        endpoint: str,
        identifiers: list[str],
        parts: str,
    ) -> list[dict[str, Any]]:
        """Fetch API resources in batches of at most 50 IDs."""

        cleaned_identifiers = unique_identifiers(identifiers)

        if not cleaned_identifiers:
            return []

        resources: list[dict[str, Any]] = []

        for start_index in range(
            0,
            len(cleaned_identifiers),
            MAX_IDS_PER_REQUEST,
        ):
            identifier_batch = cleaned_identifiers[start_index : start_index + MAX_IDS_PER_REQUEST]

            payload = self._get(
                endpoint,
                params={
                    "part": parts,
                    "id": ",".join(identifier_batch),
                },
            )

            items = payload.get("items", [])

            if not isinstance(items, list):
                raise YouTubeAPIError("YouTube returned invalid resource data.")

            resources.extend(item for item in items if isinstance(item, dict))

        return resources

    def search_video_ids(
        self,
        *,
        query: str,
        published_after: datetime,
        max_results: int = 50,
    ) -> list[str]:
        """Search recent short-duration videos."""

        cleaned_query = query.strip()

        if not cleaned_query:
            raise ValueError("query must not be empty")

        if not 1 <= max_results <= 50:
            raise ValueError("max_results must be between 1 and 50")

        payload = self._get(
            "search",
            params={
                "part": "snippet",
                "type": "video",
                "q": cleaned_query,
                "publishedAfter": format_rfc3339_utc(published_after),
                "order": "viewCount",
                "videoDuration": "short",
                "maxResults": max_results,
            },
        )

        items = payload.get("items", [])

        if not isinstance(items, list):
            raise YouTubeAPIError("YouTube returned invalid search results.")

        video_ids: list[str] = []

        for item in items:
            if not isinstance(item, dict):
                continue

            identifier = item.get("id")

            if not isinstance(identifier, dict):
                continue

            video_id = identifier.get("videoId")

            if isinstance(video_id, str):
                video_ids.append(video_id)

        return unique_identifiers(video_ids)

    def fetch_video_details(
        self,
        video_ids: list[str],
    ) -> list[VideoDetails]:
        """Fetch and parse metadata for multiple videos."""

        resources = self._fetch_resources(
            endpoint="videos",
            identifiers=video_ids,
            parts="snippet,contentDetails,statistics",
        )

        return [parse_video_resource(resource) for resource in resources]

    def fetch_channel_details(
        self,
        channel_ids: list[str],
    ) -> list[ChannelDetails]:
        """Fetch and parse metadata for multiple channels."""

        resources = self._fetch_resources(
            endpoint="channels",
            identifiers=channel_ids,
            parts="snippet,statistics",
        )

        return [parse_channel_resource(resource) for resource in resources]
