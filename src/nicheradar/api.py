"""HTTP API and frontend server for NicheRadar."""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    status,
)
from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from nicheradar.config import get_settings
from nicheradar.groq_client import (
    GroqAPIError,
    GroqClient,
)
from nicheradar.query_expansion import (
    DEFAULT_QUERY_COUNT,
    QueryExpansionError,
    expand_niche_queries,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIRECTORY = PROJECT_ROOT / "frontend"

if not FRONTEND_DIRECTORY.is_dir():
    raise RuntimeError(
        f"Frontend directory does not exist: {FRONTEND_DIRECTORY}"
    )


class QueryExpansionRequest(BaseModel):
    """Data sent by the browser when requesting query suggestions."""

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
        """Remove unnecessary whitespace and reject blank niches."""

        cleaned_niche = " ".join(value.split())

        if not cleaned_niche:
            raise ValueError("niche must not be empty")

        return cleaned_niche


class QueryExpansionResponse(BaseModel):
    """Validated query suggestions returned to the browser."""

    niche: str
    queries: list[str]


def get_groq_client() -> Iterator[GroqClient]:
    """Provide one configured Groq client for an API request."""

    settings = get_settings()

    if not settings.groq_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq API key is not configured.",
        )

    with GroqClient(settings.groq_api_key) as groq_client:
        yield groq_client


app = FastAPI(
    title="NicheRadar API",
    version="0.2.0",
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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not generate search queries right now.",
        ) from error

    return QueryExpansionResponse(
        niche=expansion.niche,
        queries=list(expansion.queries),
    )


app.frontend(
    "/",
    directory=str(FRONTEND_DIRECTORY),
)