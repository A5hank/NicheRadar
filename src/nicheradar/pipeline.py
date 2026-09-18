"""End-to-end NicheRadar analysis orchestration."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from sqlalchemy.orm import Session

from nicheradar.collector import (
    CollectionSummary,
    collect_niche,
)
from nicheradar.ranking import rank_videos
from nicheradar.repositories import get_analysis_videos_by_run
from nicheradar.results import (
    DEFAULT_RESULT_LIMIT,
    NicheResults,
    build_niche_results,
)
from nicheradar.youtube import YouTubeClient

DEFAULT_SEARCH_LIMIT = 50
ANALYSIS_RETENTION_DAYS = 30


def build_analysis_fingerprint(
    *,
    niche: str,
    search_queries: Sequence[str] | None,
) -> str:
    """Return a stable fingerprint without persisting raw request controls."""

    normalized_queries = tuple(
        " ".join(query.split()).casefold() for query in (search_queries or (niche,))
    )
    normalized_niche = " ".join(niche.split()).casefold()
    serialized_request = "\x1f".join((normalized_niche, *normalized_queries))

    return sha256(serialized_request.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class NicheAnalysis:
    """Complete collection and analysis result for one niche."""

    collection: CollectionSummary
    results: NicheResults


def run_niche_analysis(
    *,
    client: YouTubeClient,
    session: Session,
    niche: str,
    search_queries: Sequence[str] | None = None,
    analyzed_at: datetime | None = None,
    search_limit: int = DEFAULT_SEARCH_LIMIT,
    result_limit: int = DEFAULT_RESULT_LIMIT,
) -> NicheAnalysis:
    """Collect, store, score, and select niche videos."""

    analysis_time = analyzed_at or datetime.now(UTC)

    if analysis_time.tzinfo is None or analysis_time.utcoffset() is None:
        raise ValueError("analyzed_at must be timezone-aware")

    analysis_time = analysis_time.astimezone(UTC)

    collection_summary = collect_niche(
        client=client,
        session=session,
        niche=niche,
        search_queries=search_queries,
        collected_at=analysis_time,
        query_fingerprint=build_analysis_fingerprint(
            niche=niche,
            search_queries=search_queries,
        ),
        expires_at=analysis_time + timedelta(days=ANALYSIS_RETENTION_DAYS),
        max_results=search_limit,
    )

    stored_videos = get_analysis_videos_by_run(
        session,
        analysis_run_id=collection_summary.analysis_run_id,
    )

    scored_videos = rank_videos(
        stored_videos,
        as_of=analysis_time,
        limit=None,
    )

    results = build_niche_results(
        scored_videos,
        limit=result_limit,
    )

    return NicheAnalysis(
        collection=collection_summary,
        results=results,
    )
