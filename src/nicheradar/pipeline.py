"""End-to-end NicheRadar analysis orchestration."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from nicheradar.collector import (
    CollectionSummary,
    collect_niche,
)
from nicheradar.ranking import rank_videos
from nicheradar.repositories import get_videos_by_niche
from nicheradar.results import (
    DEFAULT_RESULT_LIMIT,
    NicheResults,
    build_niche_results,
)
from nicheradar.youtube import YouTubeClient

DEFAULT_SEARCH_LIMIT = 50


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
        collected_at=analysis_time,
        max_results=search_limit,
    )

    stored_videos = get_videos_by_niche(
        session,
        niche=collection_summary.niche,
        collected_date=analysis_time.date(),
        limit=None,
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
