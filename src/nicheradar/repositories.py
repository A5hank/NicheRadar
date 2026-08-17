"""Database operations for NicheRadar entities."""

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from nicheradar.models import Channel, Snapshot, Video


def upsert_channel(
    session: Session,
    *,
    channel_id: str,
    channel_name: str,
    subscriber_count: int | None,
    video_count: int | None = None,
) -> tuple[Channel, bool]:
    """Create a channel or update its latest metadata."""

    channel = session.get(Channel, channel_id)
    created = channel is None

    if channel is None:
        channel = Channel(
            channel_id=channel_id,
            channel_name=channel_name,
            subscriber_count=subscriber_count,
            video_count=video_count,
        )
        session.add(channel)
    else:
        channel.channel_name = channel_name
        channel.subscriber_count = subscriber_count
        channel.video_count = video_count

    session.flush()

    return channel, created


def upsert_video_observation(
    session: Session,
    *,
    video_id: str,
    title: str,
    url: str,
    channel_id: str,
    views: int,
    likes: int | None,
    comments: int | None,
    subscribers: int | None,
    duration_seconds: int,
    upload_date: datetime,
    niche: str,
    collected_date: date,
    tags: tuple[str, ...] = (),
    thumbnail_url: str | None = None,
) -> tuple[Video, bool]:
    """Create or update one daily video observation."""

    statement = select(Video).where(
        Video.video_id == video_id,
        Video.niche == niche,
        Video.collected_date == collected_date,
    )
    video = session.scalar(statement)
    created = video is None

    if video is None:
        video = Video(
            video_id=video_id,
            title=title,
            url=url,
            thumbnail_url=thumbnail_url,
            channel_id=channel_id,
            views=views,
            likes=likes,
            comments=comments,
            subscribers=subscribers,
            duration_seconds=duration_seconds,
            tags=list(tags),
            upload_date=upload_date,
            niche=niche,
            collected_date=collected_date,
        )
        session.add(video)
    else:
        video.title = title
        video.url = url
        video.thumbnail_url = thumbnail_url
        video.channel_id = channel_id
        video.views = views
        video.likes = likes
        video.comments = comments
        video.subscribers = subscribers
        video.duration_seconds = duration_seconds
        video.tags = list(tags)
        video.upload_date = upload_date

    session.flush()

    return video, created


def upsert_snapshot(
    session: Session,
    *,
    niche: str,
    snapshot_date: date,
    video_count: int,
    average_views: float,
    median_views: float,
) -> tuple[Snapshot, bool]:
    """Create or update a daily niche snapshot."""

    statement = select(Snapshot).where(
        Snapshot.niche == niche,
        Snapshot.snapshot_date == snapshot_date,
    )
    snapshot = session.scalar(statement)
    created = snapshot is None

    if snapshot is None:
        snapshot = Snapshot(
            niche=niche,
            snapshot_date=snapshot_date,
            video_count=video_count,
            average_views=average_views,
            median_views=median_views,
        )
        session.add(snapshot)
    else:
        snapshot.video_count = video_count
        snapshot.average_views = average_views
        snapshot.median_views = median_views

    session.flush()

    return snapshot, created


def get_videos_by_niche(
    session: Session,
    *,
    niche: str,
    collected_date: date | None = None,
    limit: int | None = 50,
) -> list[Video]:
    """Return video observations ordered by highest view count."""

    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1")

    statement = (
        select(Video)
        .options(selectinload(Video.channel))
        .where(Video.niche == niche)
        .order_by(Video.views.desc())
    )

    if collected_date is not None:
        statement = statement.where(
            Video.collected_date == collected_date,
        )

    if limit is not None:
        statement = statement.limit(limit)

    return list(session.scalars(statement))
