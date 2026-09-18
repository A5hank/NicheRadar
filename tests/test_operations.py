"""Tests for durable public-beta controls shared by all application instances."""

from datetime import UTC, date, datetime, timedelta

import pytest

from nicheradar.database import (
    create_database_engine,
    create_database_schema,
    create_session_factory,
)
from nicheradar.operations import (
    DuplicateAnalysisError,
    RateLimitExceededError,
    YouTubeBudgetExceededError,
    acquire_analysis_lock,
    cleanup_expired_records,
    consume_rate_limit,
    reserve_youtube_search_budget,
)
from nicheradar.repositories import create_analysis_run

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


@pytest.fixture
def session_factory():
    """Provide an isolated database for durable-control tests."""

    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    create_database_schema(engine)

    try:
        yield create_session_factory(engine)
    finally:
        engine.dispose()


def test_rate_limit_rejects_the_next_request_in_the_same_window(session_factory) -> None:
    """Fixed-window counts should be enforced server-side rather than in the UI."""

    with session_factory.begin() as session:
        consume_rate_limit(
            session,
            endpoint="query_expansion",
            client_key="client",
            limit=2,
            now=NOW,
        )
        consume_rate_limit(
            session,
            endpoint="query_expansion",
            client_key="client",
            limit=2,
            now=NOW,
        )

        with pytest.raises(RateLimitExceededError):
            consume_rate_limit(
                session,
                endpoint="query_expansion",
                client_key="client",
                limit=2,
                now=NOW,
            )


def test_duplicate_lock_is_shared_through_the_database(session_factory) -> None:
    """A second worker must not run the same fingerprint concurrently."""

    with session_factory.begin() as session:
        acquire_analysis_lock(
            session,
            fingerprint="a" * 64,
            expires_at=NOW + timedelta(minutes=1),
            now=NOW,
        )

    with session_factory.begin() as session:
        with pytest.raises(DuplicateAnalysisError):
            acquire_analysis_lock(
                session,
                fingerprint="a" * 64,
                expires_at=NOW + timedelta(minutes=1),
                now=NOW,
            )


def test_youtube_budget_reserves_searches_before_collection(session_factory) -> None:
    """The global search budget should reject work before provider calls start."""

    with session_factory.begin() as session:
        reserve_youtube_search_budget(
            session,
            searches=6,
            daily_budget=10,
            today=date(2026, 9, 18),
        )

    with session_factory.begin() as session:
        with pytest.raises(YouTubeBudgetExceededError):
            reserve_youtube_search_budget(
                session,
                searches=5,
                daily_budget=10,
                today=date(2026, 9, 18),
            )


def test_retention_deletes_expired_analysis_runs(session_factory) -> None:
    """Stored public API observations must not remain after their retention window."""

    with session_factory.begin() as session:
        create_analysis_run(
            session,
            niche="Minecraft",
            query_fingerprint="b" * 64,
            approved_queries=("Minecraft",),
            collected_at=NOW - timedelta(days=31),
            expires_at=NOW - timedelta(days=1),
        )

    with session_factory.begin() as session:
        deleted = cleanup_expired_records(session, now=NOW)

    assert deleted["analysis_runs"] == 1
