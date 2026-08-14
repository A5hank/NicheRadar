"""Verify access to the YouTube Data API."""

from datetime import UTC, datetime, timedelta

from nicheradar.config import get_settings
from nicheradar.youtube import YouTubeClient


def main() -> None:
    """Search for a small set of recent YouTube videos."""

    settings = get_settings()

    if not settings.youtube_api_key:
        raise RuntimeError(
            "YOUTUBE_API_KEY is missing from the environment."
        )

    published_after = datetime.now(UTC) - timedelta(days=7)

    with YouTubeClient(settings.youtube_api_key) as client:
        video_ids = client.search_video_ids(
            query="AI productivity",
            published_after=published_after,
            max_results=5,
        )

    print(
        "YouTube connection successful: "
        f"found {len(video_ids)} candidate videos."
    )

    for video_id in video_ids:
        print(
            f"https://youtube.com/watch?v={video_id}"
        )


if __name__ == "__main__":
    main()