"""HTTP API and frontend server for NicheRadar."""

import logging
from collections.abc import (
    Callable,
    Iterator,
)
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    status,
)
from fastapi.responses import FileResponse
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)
from sqlalchemy.exc import SQLAlchemyError

from nicheradar.analytics import PerformanceLabel
from nicheradar.config import get_settings
from nicheradar.database import (
    create_database_engine,
    create_database_schema,
    create_session_factory,
)
from nicheradar.groq_client import (
    GroqAPIError,
    GroqClient,
)
from nicheradar.niche_spelling import (
    NicheSpellingError,
    check_niche_spelling,
)
from nicheradar.niche_summary import (
    AnalysisSummaryFacts,
    NewCreatorSignal,
    NewCreatorSignalLabel,
    NicheSummaryError,
    determine_new_creator_signal,
    generate_niche_summary,
)
from nicheradar.pipeline import (
    NicheAnalysis,
    run_niche_analysis,
)
from nicheradar.query_expansion import (
    DEFAULT_QUERY_COUNT,
    MAX_QUERY_COUNT,
    QueryExpansionError,
    expand_niche_queries,
    normalize_query,
)
from nicheradar.query_relevance import (
    MAX_QUERIES_TO_ASSESS,
    QueryRelevanceError,
    assess_query_relevance,
)
from nicheradar.virality import (
    ConfidenceLabel,
    ViralityLabel,
    calculate_confidence_score,
    calculate_virality_score,
)
from nicheradar.youtube import YouTubeClient

LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIRECTORY = PROJECT_ROOT / "frontend"

if not FRONTEND_DIRECTORY.is_dir():
    raise RuntimeError(f"Frontend directory does not exist: {FRONTEND_DIRECTORY}")


class QueryExpansionRequest(BaseModel):
    """Data sent when requesting query suggestions."""

    niche: str = Field(
        min_length=1,
        max_length=100,
    )

    @field_validator("niche")
    @classmethod
    def normalize_niche(
        cls,
        value: str,
    ) -> str:
        """Normalize and validate the requested niche."""

        cleaned_niche = normalize_query(value)

        if not cleaned_niche:
            raise ValueError("niche must not be empty")

        return cleaned_niche


class QueryExpansionResponse(BaseModel):
    """Validated query suggestions returned to the browser."""

    niche: str
    queries: list[str]


class NicheSpellingRequest(BaseModel):
    """A niche to check before query expansion."""

    niche: str = Field(
        min_length=1,
        max_length=100,
    )

    @field_validator("niche")
    @classmethod
    def normalize_niche(
        cls,
        value: str,
    ) -> str:
        """Normalize and validate the niche being checked."""

        cleaned_niche = normalize_query(value)

        if not cleaned_niche:
            raise ValueError("niche must not be empty")

        return cleaned_niche


class NicheSpellingResponse(BaseModel):
    """A conservative web-assisted search suggestion for the original niche."""

    niche: str
    suggestion: str | None


class AnalysisSummaryContext(BaseModel):
    """Validated completed-analysis facts used for the optional summary."""

    query_count: int = Field(ge=1, le=MAX_QUERY_COUNT)
    videos_considered: int = Field(ge=0)
    videos_returned: int = Field(ge=0)
    videos_with_subscriber_data: int = Field(ge=0)
    breakout_count: int = Field(ge=0)
    breakout_channel_count: int = Field(ge=0)
    exceptional_count: int = Field(ge=0)
    unique_channel_count: int = Field(ge=0)
    virality_score: int = Field(ge=0, le=100)
    confidence_score: int = Field(ge=0, le=100)
    median_views_per_day: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_summary_facts(
        self,
    ) -> "AnalysisSummaryContext":
        """Ensure the browser cannot submit contradictory summary facts."""

        self.to_facts()

        return self

    def to_facts(
        self,
    ) -> AnalysisSummaryFacts:
        """Convert the browser-safe context to the summary domain model."""

        return AnalysisSummaryFacts(
            query_count=self.query_count,
            videos_considered=self.videos_considered,
            videos_returned=self.videos_returned,
            videos_with_subscriber_data=self.videos_with_subscriber_data,
            breakout_count=self.breakout_count,
            breakout_channel_count=self.breakout_channel_count,
            exceptional_count=self.exceptional_count,
            unique_channel_count=self.unique_channel_count,
            virality_score=self.virality_score,
            confidence_score=self.confidence_score,
            median_views_per_day=self.median_views_per_day,
        )


class AnalysisSummaryRequest(BaseModel):
    """Completed facts sent for optional AI explanation only."""

    niche: str = Field(min_length=1, max_length=100)
    summary_context: AnalysisSummaryContext

    @field_validator("niche")
    @classmethod
    def normalize_niche(
        cls,
        value: str,
    ) -> str:
        """Normalize the niche without treating it as prompt instructions."""

        cleaned_niche = normalize_query(value)

        if not cleaned_niche:
            raise ValueError("niche must not be empty")

        return cleaned_niche


class NewCreatorSignalResponse(BaseModel):
    """Deterministic new-creator interpretation shown beneath the summary."""

    label: NewCreatorSignalLabel
    rationale: str


class AnalysisSummaryResponse(BaseModel):
    """Optional AI observations plus a deterministic new-creator signal."""

    niche: str
    observations: list[str] | None
    new_creator_signal: NewCreatorSignalResponse


class QueryRelevanceRequest(BaseModel):
    """User-added queries that should be checked for relevance."""

    niche: str = Field(
        min_length=1,
        max_length=100,
    )
    queries: list[str] = Field(
        min_length=1,
        max_length=MAX_QUERIES_TO_ASSESS,
    )

    @field_validator("niche")
    @classmethod
    def normalize_niche(
        cls,
        value: str,
    ) -> str:
        """Normalize and validate the original niche."""

        cleaned_niche = normalize_query(value)

        if not cleaned_niche:
            raise ValueError("niche must not be empty")

        return cleaned_niche

    @field_validator("queries")
    @classmethod
    def validate_queries(
        cls,
        values: list[str],
    ) -> list[str]:
        """Normalize and require unique non-empty queries."""

        cleaned_queries = [normalize_query(value) for value in values]

        if any(not query for query in cleaned_queries):
            raise ValueError("queries must not contain empty values")

        comparison_keys = {query.casefold() for query in cleaned_queries}

        if len(comparison_keys) != len(cleaned_queries):
            raise ValueError("queries must be unique")

        return cleaned_queries


class QueryRelevanceWarningResponse(BaseModel):
    """One query that may not belong to the niche."""

    query: str
    reason: str


class QueryRelevanceResponse(BaseModel):
    """Browser-facing warnings for reviewed queries."""

    niche: str
    warnings: list[QueryRelevanceWarningResponse]


class AnalysisRequest(BaseModel):
    """One to ten approved search queries submitted for analysis."""

    niche: str = Field(
        min_length=1,
        max_length=100,
    )
    queries: list[str] = Field(
        min_length=1,
        max_length=MAX_QUERY_COUNT,
    )

    @field_validator("niche")
    @classmethod
    def normalize_niche(
        cls,
        value: str,
    ) -> str:
        """Normalize and validate the submitted niche."""

        cleaned_niche = normalize_query(value)

        if not cleaned_niche:
            raise ValueError("niche must not be empty")

        return cleaned_niche

    @field_validator("queries")
    @classmethod
    def validate_queries(
        cls,
        values: list[str],
    ) -> list[str]:
        """Require unique, non-empty search queries."""

        cleaned_queries = [normalize_query(value) for value in values]

        if any(not query for query in cleaned_queries):
            raise ValueError("queries must not contain empty values")

        comparison_keys = {query.casefold() for query in cleaned_queries}

        if len(comparison_keys) != len(cleaned_queries):
            raise ValueError("queries must be unique")

        return cleaned_queries

    @model_validator(mode="after")
    def require_original_niche_first(
        self,
    ) -> "AnalysisRequest":
        """Require the locked original niche as query one."""

        if self.queries[0].casefold() != self.niche.casefold():
            raise ValueError("queries must begin with the original niche")

        return self


class AnalysisVideoResponse(BaseModel):
    """One scored video returned to the dashboard."""

    rank: int
    video_id: str
    title: str
    url: str
    thumbnail_url: str | None = None
    channel_name: str
    upload_date: datetime
    views: int
    views_per_day: float
    subscribers: int | None
    subscriber_multiplier: float | None
    performance: PerformanceLabel


class ViralityBreakdownResponse(BaseModel):
    """Component values used by the expandable score breakdown."""

    breakout_points: int
    velocity_points: int
    exceptional_points: int
    diversity_points: int
    median_views_per_day: float
    unique_channel_count: int


class ViralityScoreResponse(BaseModel):
    """Browser-facing Virality Score information."""

    score: int
    label: ViralityLabel
    breakdown: ViralityBreakdownResponse


class ConfidenceScoreResponse(BaseModel):
    """Browser-facing Confidence Score information."""

    score: int
    label: ConfidenceLabel


class AnalysisResponse(BaseModel):
    """Complete browser-facing NicheRadar result."""

    niche: str
    queries: list[str]
    videos_considered: int
    videos_returned: int
    breakout_count: int
    exceptional_performance_count: int
    virality_score: ViralityScoreResponse
    confidence_score: ConfidenceScoreResponse
    summary_context: AnalysisSummaryContext
    videos: list[AnalysisVideoResponse]


AnalysisRunner = Callable[
    [AnalysisRequest],
    NicheAnalysis,
]


def get_groq_client() -> Iterator[GroqClient]:
    """Provide one configured Groq client per request."""

    settings = get_settings()

    if not settings.groq_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq API key is not configured.",
        )

    with GroqClient(settings.groq_api_key) as groq_client:
        yield groq_client


def get_optional_groq_client() -> Iterator[GroqClient | None]:
    """Provide Groq when configured, or let an advisory feature fail open."""

    settings = get_settings()

    if not settings.groq_api_key:
        yield None
        return

    with GroqClient(settings.groq_api_key) as groq_client:
        yield groq_client


def execute_niche_analysis(
    request: AnalysisRequest,
) -> NicheAnalysis:
    """Run the existing analysis pipeline for an API request."""

    settings = get_settings()

    if not settings.youtube_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YouTube API key is not configured.",
        )

    engine = create_database_engine(settings.database_url)

    try:
        create_database_schema(engine)
        session_factory = create_session_factory(engine)

        with YouTubeClient(settings.youtube_api_key) as youtube_client:
            with session_factory.begin() as session:
                return run_niche_analysis(
                    client=youtube_client,
                    session=session,
                    niche=request.niche,
                    search_queries=tuple(request.queries),
                )
    finally:
        engine.dispose()


def get_analysis_runner() -> AnalysisRunner:
    """Provide the analysis function used by the endpoint."""

    return execute_niche_analysis


def build_analysis_response(
    request: AnalysisRequest,
    analysis: NicheAnalysis,
) -> AnalysisResponse:
    """Convert internal analysis dataclasses into API models."""

    result_videos = analysis.results.videos

    videos = [
        AnalysisVideoResponse(
            rank=rank,
            video_id=video.video_id,
            title=video.title,
            url=video.url,
            thumbnail_url=video.thumbnail_url,
            channel_name=video.channel_name,
            upload_date=video.upload_date,
            views=video.views,
            views_per_day=(video.metrics.views_per_day),
            subscribers=video.subscribers,
            subscriber_multiplier=(video.metrics.subscriber_multiplier),
            performance=(video.metrics.performance_label),
        )
        for rank, video in enumerate(
            result_videos,
            start=1,
        )
    ]

    unique_channel_count = len({video.channel_id for video in result_videos})

    videos_with_subscriber_data = sum(video.subscribers is not None for video in result_videos)

    breakout_channel_count = len(
        {
            video.channel_id
            for video in result_videos
            if video.metrics.performance_label is PerformanceLabel.BREAKOUT
        }
    )

    virality = calculate_virality_score(
        views_per_day=(video.metrics.views_per_day for video in result_videos),
        breakout_count=(analysis.results.breakout_count),
        exceptional_count=(analysis.results.exceptional_performance_count),
        unique_channel_count=(unique_channel_count),
    )

    confidence = calculate_confidence_score(
        query_count=len(request.queries),
        videos_considered=(analysis.results.considered_count),
        videos_returned=(analysis.results.total_count),
        videos_with_subscriber_data=(videos_with_subscriber_data),
    )

    return AnalysisResponse(
        niche=request.niche,
        queries=request.queries,
        videos_considered=(analysis.results.considered_count),
        videos_returned=(analysis.results.total_count),
        breakout_count=(analysis.results.breakout_count),
        exceptional_performance_count=(analysis.results.exceptional_performance_count),
        virality_score=ViralityScoreResponse(
            score=virality.score,
            label=virality.label,
            breakdown=ViralityBreakdownResponse(
                breakout_points=(virality.breakout_points),
                velocity_points=(virality.velocity_points),
                exceptional_points=(virality.exceptional_points),
                diversity_points=(virality.diversity_points),
                median_views_per_day=(virality.median_views_per_day),
                unique_channel_count=(virality.unique_channel_count),
            ),
        ),
        confidence_score=ConfidenceScoreResponse(
            score=confidence.score,
            label=confidence.label,
        ),
        summary_context=AnalysisSummaryContext(
            query_count=len(request.queries),
            videos_considered=analysis.results.considered_count,
            videos_returned=analysis.results.total_count,
            videos_with_subscriber_data=videos_with_subscriber_data,
            breakout_count=analysis.results.breakout_count,
            breakout_channel_count=breakout_channel_count,
            exceptional_count=analysis.results.exceptional_performance_count,
            unique_channel_count=unique_channel_count,
            virality_score=virality.score,
            confidence_score=confidence.score,
            median_views_per_day=virality.median_views_per_day,
        ),
        videos=videos,
    )


app = FastAPI(
    title="NicheRadar API",
    version="0.9.0",
)


@app.get(
    "/api/health",
    tags=["system"],
)
def health_check() -> dict[str, str]:
    """Confirm that the NicheRadar API is running."""

    return {
        "status": "ok",
    }


@app.post(
    "/api/niche-spelling",
    response_model=NicheSpellingResponse,
    tags=["analysis"],
)
def check_entered_niche_spelling(
    request: NicheSpellingRequest,
    groq_client: Annotated[
        GroqClient | None,
        Depends(get_optional_groq_client),
    ],
) -> NicheSpellingResponse:
    """Offer only high-confidence spelling corrections before query expansion."""

    if groq_client is None:
        return NicheSpellingResponse(
            niche=request.niche,
            suggestion=None,
        )

    try:
        spelling_check = check_niche_spelling(
            groq_client,
            request.niche,
        )
    except (
        GroqAPIError,
        NicheSpellingError,
    ):
        LOGGER.warning(
            "Niche spelling check failed for %r; continuing without a suggestion.",
            request.niche,
            exc_info=True,
        )

        return NicheSpellingResponse(
            niche=request.niche,
            suggestion=None,
        )

    return NicheSpellingResponse(
        niche=spelling_check.niche,
        suggestion=spelling_check.suggestion,
    )


@app.post(
    "/api/analysis-summary",
    response_model=AnalysisSummaryResponse,
    tags=["analysis"],
)
def generate_analysis_summary(
    request: AnalysisSummaryRequest,
    groq_client: Annotated[
        GroqClient | None,
        Depends(get_optional_groq_client),
    ],
) -> AnalysisSummaryResponse:
    """Generate optional observations without rerunning the analysis pipeline."""

    facts = request.summary_context.to_facts()
    new_creator_signal: NewCreatorSignal = determine_new_creator_signal(facts)
    observations: list[str] | None = None

    if groq_client is not None:
        try:
            observations = list(
                generate_niche_summary(
                    groq_client,
                    niche=request.niche,
                    facts=facts,
                )
            )
        except (
            GroqAPIError,
            NicheSummaryError,
            ValueError,
        ):
            LOGGER.warning(
                "AI niche summary failed for %r; keeping the deterministic dashboard available.",
                request.niche,
                exc_info=True,
            )

    return AnalysisSummaryResponse(
        niche=request.niche,
        observations=observations,
        new_creator_signal=NewCreatorSignalResponse(
            label=new_creator_signal.label,
            rationale=new_creator_signal.rationale,
        ),
    )


@app.post(
    "/api/queries",
    response_model=QueryExpansionResponse,
    tags=["analysis"],
)
def generate_search_queries(
    request: QueryExpansionRequest,
    groq_client: Annotated[
        GroqClient,
        Depends(get_groq_client),
    ],
) -> QueryExpansionResponse:
    """Generate focused YouTube searches for a niche."""

    try:
        expansion = expand_niche_queries(
            groq_client,
            request.niche,
            query_count=DEFAULT_QUERY_COUNT,
        )
    except (
        GroqAPIError,
        QueryExpansionError,
    ) as error:
        LOGGER.exception(
            "Query expansion failed for niche %r.",
            request.niche,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=("Could not generate search queries right now."),
        ) from error

    return QueryExpansionResponse(
        niche=expansion.niche,
        queries=list(expansion.queries),
    )


@app.post(
    "/api/query-relevance",
    response_model=QueryRelevanceResponse,
    tags=["analysis"],
)
def review_query_relevance(
    request: QueryRelevanceRequest,
    groq_client: Annotated[
        GroqClient,
        Depends(get_groq_client),
    ],
) -> QueryRelevanceResponse:
    """Warn about manually changed queries that seem unrelated."""

    try:
        review = assess_query_relevance(
            groq_client,
            request.niche,
            request.queries,
        )
    except (
        GroqAPIError,
        QueryRelevanceError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=("Could not verify query relevance right now."),
        ) from error

    warnings = [
        QueryRelevanceWarningResponse(
            query=warning.query,
            reason=warning.reason,
        )
        for warning in review.warnings
    ]

    return QueryRelevanceResponse(
        niche=review.niche,
        warnings=warnings,
    )


@app.post(
    "/api/analyses",
    response_model=AnalysisResponse,
    tags=["analysis"],
)
def analyze_niche(
    request: AnalysisRequest,
    analysis_runner: Annotated[
        AnalysisRunner,
        Depends(get_analysis_runner),
    ],
) -> AnalysisResponse:
    """Run NicheRadar using the approved queries."""

    try:
        analysis = analysis_runner(request)
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=("Could not access the NicheRadar analysis database."),
        ) from error
    except RuntimeError as error:
        # Preserve the upstream cause in server logs without exposing it to the browser.
        LOGGER.exception(
            "YouTube analysis failed for niche %r with %d approved queries.",
            request.niche,
            len(request.queries),
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=("Could not complete the YouTube analysis right now."),
        ) from error

    return build_analysis_response(
        request,
        analysis,
    )


app.frontend(
    "/",
    directory=str(FRONTEND_DIRECTORY),
)


@app.get(
    "/about",
    include_in_schema=False,
)
def serve_about_page() -> FileResponse:
    """Serve the standalone NicheRadar About page."""

    return FileResponse(
        FRONTEND_DIRECTORY / "about.html",
        media_type="text/html",
    )
