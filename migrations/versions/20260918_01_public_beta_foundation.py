"""Create isolated run and operational-control tables.

Revision ID: 20260918_01
Revises:
Create Date: 2026-09-18
"""

import sqlalchemy as sa
from alembic import op

revision = "20260918_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create active tables without modifying legacy local observations."""

    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("niche", sa.String(length=255), nullable=False),
        sa.Column("query_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("approved_queries", sa.JSON(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_runs"),
    )
    op.create_index("ix_analysis_runs_expires_at", "analysis_runs", ["expires_at"])
    op.create_index("ix_analysis_runs_fingerprint", "analysis_runs", ["query_fingerprint"])

    op.create_table(
        "analysis_videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("video_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=1000), nullable=True),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("channel_name", sa.String(length=255), nullable=False),
        sa.Column("views", sa.BigInteger(), nullable=False),
        sa.Column("likes", sa.BigInteger(), nullable=True),
        sa.Column("comments", sa.BigInteger(), nullable=True),
        sa.Column("subscribers", sa.BigInteger(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("upload_date", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "views >= 0",
            name="ck_analysis_videos_non_negative_analysis_video_views",
        ),
        sa.CheckConstraint(
            "subscribers IS NULL OR subscribers >= 0",
            name="ck_analysis_videos_non_negative_analysis_video_subscribers",
        ),
        sa.CheckConstraint(
            "duration_seconds >= 0",
            name="ck_analysis_videos_non_negative_analysis_video_duration",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name="fk_analysis_videos_analysis_run_id_analysis_runs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_videos"),
        sa.UniqueConstraint(
            "analysis_run_id",
            "video_id",
            name="uq_analysis_video_run_video",
        ),
    )
    op.create_index("ix_analysis_videos_analysis_run_id", "analysis_videos", ["analysis_run_id"])
    op.create_index(
        "ix_analysis_videos_run_views",
        "analysis_videos",
        ["analysis_run_id", "views"],
    )

    op.create_table(
        "analysis_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("video_count", sa.Integer(), nullable=False),
        sa.Column("average_views", sa.Float(), nullable=False),
        sa.Column("median_views", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "video_count >= 0",
            name="ck_analysis_snapshots_non_negative_video_count",
        ),
        sa.CheckConstraint(
            "average_views >= 0",
            name="ck_analysis_snapshots_non_negative_average_views",
        ),
        sa.CheckConstraint(
            "median_views >= 0",
            name="ck_analysis_snapshots_non_negative_median_views",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name="fk_analysis_snapshots_analysis_run_id_analysis_runs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_snapshots"),
        sa.UniqueConstraint("analysis_run_id", name="uq_analysis_snapshot_run"),
    )
    op.create_index(
        "ix_analysis_snapshots_analysis_run_id",
        "analysis_snapshots",
        ["analysis_run_id"],
    )

    op.create_table(
        "analysis_locks",
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("fingerprint", name="pk_analysis_locks"),
    )
    op.create_index("ix_analysis_locks_expires_at", "analysis_locks", ["expires_at"])

    op.create_table(
        "youtube_daily_budgets",
        sa.Column("budget_date", sa.Date(), nullable=False),
        sa.Column("searches_reserved", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("budget_date", name="pk_youtube_daily_budgets"),
    )

    op.create_table(
        "request_rate_limits",
        sa.Column("endpoint", sa.String(length=64), nullable=False),
        sa.Column("client_key", sa.String(length=64), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint(
            "endpoint",
            "client_key",
            "window_started_at",
            name="pk_request_rate_limits",
        ),
    )


def downgrade() -> None:
    """Remove active public-beta storage tables in dependency order."""

    op.drop_table("request_rate_limits")
    op.drop_table("youtube_daily_budgets")
    op.drop_index("ix_analysis_locks_expires_at", table_name="analysis_locks")
    op.drop_table("analysis_locks")
    op.drop_index("ix_analysis_snapshots_analysis_run_id", table_name="analysis_snapshots")
    op.drop_table("analysis_snapshots")
    op.drop_index("ix_analysis_videos_run_views", table_name="analysis_videos")
    op.drop_index("ix_analysis_videos_analysis_run_id", table_name="analysis_videos")
    op.drop_table("analysis_videos")
    op.drop_index("ix_analysis_runs_fingerprint", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_expires_at", table_name="analysis_runs")
    op.drop_table("analysis_runs")
