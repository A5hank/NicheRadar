"""Durable public-beta controls backed by the shared application database."""

from datetime import UTC, date, datetime, timedelta
from hashlib import sha256

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from nicheradar.models import (
    AnalysisLock,
    AnalysisRun,
    RequestRateLimit,
    YouTubeDailyBudget,
)


class DuplicateAnalysisError(RuntimeError):
    """Raised when the same normalized analysis is already running."""


class RateLimitExceededError(RuntimeError):
    """Raised when a client has used its fixed-window allowance."""


class YouTubeBudgetExceededError(RuntimeError):
    """Raised before a request would exceed the daily YouTube search budget."""


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for operational records."""

    return datetime.now(UTC)


def client_key_from_address(address: str | None) -> str:
    """Create a non-reversible key for rate limiting without logging an address."""

    normalized_address = (address or "unknown").strip().casefold()
    return sha256(normalized_address.encode("utf-8")).hexdigest()


def fixed_window_start(now: datetime) -> datetime:
    """Round one UTC instant down to the current minute."""

    return now.astimezone(UTC).replace(second=0, microsecond=0)


def consume_rate_limit(
    session: Session,
    *,
    endpoint: str,
    client_key: str,
    limit: int,
    now: datetime | None = None,
) -> None:
    """Atomically reserve one fixed-window request allowance."""

    if limit < 1:
        raise ValueError("limit must be at least 1")

    current_time = now or utc_now()
    window_started_at = fixed_window_start(current_time)
    filters = (
        RequestRateLimit.endpoint == endpoint,
        RequestRateLimit.client_key == client_key,
        RequestRateLimit.window_started_at == window_started_at,
    )
    increment = (
        update(RequestRateLimit)
        .where(*filters, RequestRateLimit.request_count < limit)
        .values(request_count=RequestRateLimit.request_count + 1)
    )

    if session.execute(increment).rowcount == 1:
        return

    try:
        with session.begin_nested():
            session.add(
                RequestRateLimit(
                    endpoint=endpoint,
                    client_key=client_key,
                    window_started_at=window_started_at,
                    request_count=1,
                )
            )
            session.flush()
    except IntegrityError:
        if session.execute(increment).rowcount == 1:
            return

        raise RateLimitExceededError from None


def reserve_youtube_search_budget(
    session: Session,
    *,
    searches: int,
    daily_budget: int,
    today: date | None = None,
) -> None:
    """Atomically reserve search calls before an analysis starts."""

    if searches < 1:
        raise ValueError("searches must be at least 1")

    if daily_budget < 1:
        raise ValueError("daily_budget must be at least 1")

    if searches > daily_budget:
        raise YouTubeBudgetExceededError

    budget_date = today or utc_now().date()
    increment = (
        update(YouTubeDailyBudget)
        .where(
            YouTubeDailyBudget.budget_date == budget_date,
            YouTubeDailyBudget.searches_reserved + searches <= daily_budget,
        )
        .values(searches_reserved=YouTubeDailyBudget.searches_reserved + searches)
    )

    if session.execute(increment).rowcount == 1:
        return

    try:
        with session.begin_nested():
            session.add(
                YouTubeDailyBudget(
                    budget_date=budget_date,
                    searches_reserved=searches,
                )
            )
            session.flush()
    except IntegrityError:
        if session.execute(increment).rowcount == 1:
            return

        raise YouTubeBudgetExceededError from None


def acquire_analysis_lock(
    session: Session,
    *,
    fingerprint: str,
    expires_at: datetime,
    now: datetime | None = None,
) -> None:
    """Acquire an atomic cross-instance lock or reject a duplicate request."""

    current_time = now or utc_now()
    session.execute(delete(AnalysisLock).where(AnalysisLock.expires_at <= current_time))

    try:
        with session.begin_nested():
            session.add(
                AnalysisLock(
                    fingerprint=fingerprint,
                    expires_at=expires_at,
                )
            )
            session.flush()
    except IntegrityError:
        raise DuplicateAnalysisError from None


def release_analysis_lock(
    session: Session,
    *,
    fingerprint: str,
) -> None:
    """Release one completed or failed analysis lock."""

    session.execute(delete(AnalysisLock).where(AnalysisLock.fingerprint == fingerprint))


def cleanup_expired_records(
    session: Session,
    *,
    now: datetime | None = None,
) -> dict[str, int]:
    """Remove expired public-data observations and operational bookkeeping."""

    current_time = now or utc_now()
    rate_limit_cutoff = current_time - timedelta(days=2)
    budget_cutoff = current_time.date() - timedelta(days=2)

    deleted_runs = session.execute(
        delete(AnalysisRun).where(AnalysisRun.expires_at <= current_time)
    ).rowcount
    deleted_locks = session.execute(
        delete(AnalysisLock).where(AnalysisLock.expires_at <= current_time)
    ).rowcount
    deleted_rate_limits = session.execute(
        delete(RequestRateLimit).where(RequestRateLimit.window_started_at < rate_limit_cutoff)
    ).rowcount
    deleted_budgets = session.execute(
        delete(YouTubeDailyBudget).where(YouTubeDailyBudget.budget_date < budget_cutoff)
    ).rowcount

    return {
        "analysis_runs": deleted_runs or 0,
        "analysis_locks": deleted_locks or 0,
        "rate_limits": deleted_rate_limits or 0,
        "youtube_budgets": deleted_budgets or 0,
    }
