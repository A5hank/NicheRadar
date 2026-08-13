"""SQLAlchemy ORM models for NicheRadar."""

from datetime import UTC, date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    MetaData,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": ("fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"),
    "pk": "pk_%(table_name)s",
}

MODEL_METADATA = MetaData(
    naming_convention=NAMING_CONVENTION,
)


class Base(DeclarativeBase):
    """Base class inherited by every NicheRadar ORM model."""

    metadata = MODEL_METADATA


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""

    return datetime.now(UTC)


def utc_today() -> date:
    """Return the current date in UTC."""

    return utc_now().date()


class Channel(Base):
    """A YouTube channel and its latest known metadata."""

    __tablename__ = "channels"
    __table_args__ = (
        CheckConstraint(
            "subscriber_count >= 0",
            name="non_negative_subscriber_count",
        ),
    )

    channel_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    channel_name: Mapped[str] = mapped_column(
        String(255),
    )
    subscriber_count: Mapped[int] = mapped_column(
        BigInteger,
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    videos: Mapped[list["Video"]] = relationship(
        back_populates="channel",
    )


class Video(Base):
    """A video observation collected for a particular niche and date."""

    __tablename__ = "videos"
    __table_args__ = (
        UniqueConstraint(
            "video_id",
            "niche",
            "collected_date",
            name="uq_video_niche_collection_date",
        ),
        CheckConstraint(
            "views >= 0",
            name="non_negative_views",
        ),
        CheckConstraint(
            "likes >= 0",
            name="non_negative_likes",
        ),
        CheckConstraint(
            "comments >= 0",
            name="non_negative_comments",
        ),
        CheckConstraint(
            "subscribers >= 0",
            name="non_negative_subscribers",
        ),
        CheckConstraint(
            "duration_seconds >= 0",
            name="non_negative_duration",
        ),
        Index(
            "ix_videos_niche_upload_date",
            "niche",
            "upload_date",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )
    video_id: Mapped[str] = mapped_column(
        String(32),
    )
    title: Mapped[str] = mapped_column(
        Text,
    )
    url: Mapped[str] = mapped_column(
        String(500),
    )

    channel_id: Mapped[str] = mapped_column(
        ForeignKey(
            "channels.channel_id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    views: Mapped[int] = mapped_column(
        BigInteger,
    )
    likes: Mapped[int] = mapped_column(
        BigInteger,
    )
    comments: Mapped[int] = mapped_column(
        BigInteger,
    )
    subscribers: Mapped[int] = mapped_column(
        BigInteger,
    )
    duration_seconds: Mapped[int] = mapped_column()

    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    niche: Mapped[str] = mapped_column(
        String(255),
    )
    collected_date: Mapped[date] = mapped_column(
        Date,
        default=utc_today,
    )

    channel: Mapped[Channel] = relationship(
        back_populates="videos",
    )


class Snapshot(Base):
    """Daily aggregate metrics for a niche."""

    __tablename__ = "snapshots"
    __table_args__ = (
        UniqueConstraint(
            "niche",
            "date",
            name="uq_snapshot_niche_date",
        ),
        CheckConstraint(
            "video_count >= 0",
            name="non_negative_video_count",
        ),
        CheckConstraint(
            "average_views >= 0",
            name="non_negative_average_views",
        ),
        CheckConstraint(
            "median_views >= 0",
            name="non_negative_median_views",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )
    niche: Mapped[str] = mapped_column(
        String(255),
    )
    snapshot_date: Mapped[date] = mapped_column(
        "date",
        Date,
    )
    video_count: Mapped[int] = mapped_column()
    average_views: Mapped[float] = mapped_column(
        Float,
    )
    median_views: Mapped[float] = mapped_column(
        Float,
    )
