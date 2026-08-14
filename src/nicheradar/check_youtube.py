"""Verify access to YouTube video and channel metadata."""

from datetime import UTC, datetime, timedelta

from nicheradar.config import get_settings
from nicheradar.youtube import YouTubeClient


def main() -> None:
    """Fetch and display recent candidate Short metadata."""

    settings = get_settings()

    if not settings.youtube_api_key:
        raise RuntimeError("YOUTUBE_API_KEY is missing from the environment.")

    published_after = datetime.now(UTC) - timedelta(days=7)

    with YouTubeClient(settings.youtube_api_key) as client:
        video_ids = client.search_video_ids(
            query="Minecraft",
            published_after=published_after,
            max_results=5,
        )

        videos = client.fetch_video_details(video_ids)

        channel_ids = [video.channel_id for video in videos]
        channels = client.fetch_channel_details(channel_ids)

    channels_by_id = {channel.channel_id: channel for channel in channels}

    short_candidates = [video for video in videos if video.is_short_candidate]

    print(f"YouTube connection successful: found {len(short_candidates)} Short candidates.")

    for video in short_candidates:
        channel = channels_by_id.get(video.channel_id)

        subscribers = channel.subscriber_count if channel is not None else None

        print()
        print(video.title)
        print(f"Views: {video.view_count}")
        print(f"Subscribers: {subscribers}")
        print(f"Duration: {video.duration_seconds}s")
        print(video.url)


if __name__ == "__main__":
    main()
