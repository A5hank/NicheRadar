"""Client utilities for the YouTube Data API."""

from datetime import UTC, datetime
from types import TracebackType
from typing import Any, Self

import httpx

YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3/"
DEFAULT_TIMEOUT_SECONDS = 10.0


class YouTubeAPIError(RuntimeError):
    """Raised when a YouTube Data API request fails."""


def format_rfc3339_utc(value: datetime) -> str:
    """Convert a timezone-aware datetime to an RFC 3339 UTC value."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("value must be timezone-aware")

    utc_value = value.astimezone(UTC)

    return utc_value.isoformat(
        timespec="seconds",
    ).replace("+00:00", "Z")


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
        """Close network resources when leaving a context manager."""

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
        except httpx.RequestError as error:
            raise YouTubeAPIError("Unable to reach the YouTube Data API.") from error

        if response.is_error:
            try:
                payload = response.json()
                detail = payload["error"]["message"]
            except (KeyError, TypeError, ValueError):
                detail = "YouTube returned an unspecified error."

            raise YouTubeAPIError(
                f"YouTube API request failed with status {response.status_code}: {detail}"
            )

        payload = response.json()

        if not isinstance(payload, dict):
            raise YouTubeAPIError("YouTube returned an unexpected response.")

        return payload

    def search_video_ids(
        self,
        *,
        query: str,
        published_after: datetime,
        max_results: int = 50,
    ) -> list[str]:
        """Search recent short-duration videos and return their IDs."""

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

        return video_ids
