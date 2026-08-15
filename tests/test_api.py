"""Tests for the NicheRadar HTTP API."""

from collections.abc import Iterator
from datetime import (
    UTC,
    datetime,
)
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from nicheradar.analytics import PerformanceLabel
from nicheradar.api import (
    AnalysisRequest,
    app,
    get_analysis_runner,
    get_groq_client,
)
from nicheradar.groq_client import (
    GroqAPIError,
    GroqClient,
)


@pytest.fixture
def groq_client() -> Mock:
    """Create a fake Groq client."""

    return Mock(spec=GroqClient)


@pytest.fixture
def analysis_runner() -> Mock:
    """Create a fake complete-analysis function."""

    return Mock()


@pytest.fixture
def client(
    groq_client: Mock,
    analysis_runner: Mock,
) -> Iterator[TestClient]:
    """Create an API client using fake dependencies."""

    def override_groq_client() -> Iterator[Mock]:
        yield groq_client

    def override_analysis_runner() -> Mock:
        return analysis_runner

    app.dependency_overrides[get_groq_client] = (
        override_groq_client
    )
    app.dependency_overrides[get_analysis_runner] = (
        override_analysis_runner
    )

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_health_check_returns_ok(
    client: TestClient,
) -> None:
    """The health endpoint should confirm the API is running."""

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
    }


def test_frontend_homepage_is_served(
    client: TestClient,
) -> None:
    """The API should serve the NicheRadar homepage."""

    response = client.get("/")

    assert response.status_code == 200
    assert "NicheRadar" in response.text


def test_frontend_assets_are_served(
    client: TestClient,
) -> None:
    """The browser should be able to load frontend assets."""

    css_response = client.get("/styles.css")
    javascript_response = client.get("/app.js")

    assert css_response.status_code == 200
    assert javascript_response.status_code == 200

def test_analysis_request_accepts_original_niche_only() -> None:
    """A single locked niche query should be valid."""

    request = AnalysisRequest(
        niche="  Marvel  ",
        queries=[
            " Marvel ",
        ],
    )

    assert request.niche == "Marvel"
    assert request.queries == ["Marvel"]


def test_analysis_request_rejects_missing_original_niche() -> None:
    """The first query must match the submitted niche."""

    with pytest.raises(
        ValueError,
        match="begin with the original niche",
    ):
        AnalysisRequest(
            niche="Marvel",
            queries=[
                "MCU theories",
            ],
        )


def test_analysis_request_rejects_more_than_five_queries() -> None:
    """The API must reject a sixth query."""

    with pytest.raises(ValueError):
        AnalysisRequest(
            niche="Marvel",
            queries=[
                "Marvel",
                "Marvel news",
                "MCU theories",
                "Marvel facts",
                "Marvel trailers",
                "Marvel interviews",
            ],
        )


def test_query_endpoint_returns_expanded_queries(
    client: TestClient,
    groq_client: Mock,
) -> None:
    """The endpoint should return validated suggestions."""

    groq_client.generate_json.return_value = {
        "queries": [
            "MCU theories",
            "Marvel casting news",
            "Avengers analysis",
            "Marvel character stories",
        ]
    }

    response = client.post(
        "/api/queries",
        json={
            "niche": "  Marvel  ",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "niche": "Marvel",
        "queries": [
            "Marvel",
            "MCU theories",
            "Marvel casting news",
            "Avengers analysis",
            "Marvel character stories",
        ],
    }
    groq_client.generate_json.assert_called_once()


def test_query_endpoint_rejects_blank_niche(
    client: TestClient,
    groq_client: Mock,
) -> None:
    """The endpoint should reject blank niches."""

    response = client.post(
        "/api/queries",
        json={
            "niche": "   ",
        },
    )

    assert response.status_code == 422
    groq_client.generate_json.assert_not_called()


def test_query_endpoint_handles_groq_failure(
    client: TestClient,
    groq_client: Mock,
) -> None:
    """A Groq failure should become an HTTP response."""

    groq_client.generate_json.side_effect = GroqAPIError(
        "Could not connect to the Groq API."
    )

    response = client.post(
        "/api/queries",
        json={
            "niche": "Marvel",
        },
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": (
            "Could not generate search queries right now."
        ),
    }


def test_analysis_endpoint_returns_dashboard_data(
    client: TestClient,
    analysis_runner: Mock,
) -> None:
    """The endpoint should serialize complete analysis data."""

    video = SimpleNamespace(
        video_id="video-123",
        title="Marvel Theory Explained",
        url="https://www.youtube.com/watch?v=video-123",
        channel_name="Marvel Analyst",
        upload_date=datetime(
            2026,
            8,
            14,
            12,
            0,
            tzinfo=UTC,
        ),
        views=250_000,
        subscribers=5_000,
        metrics=SimpleNamespace(
            views_per_day=125_000.0,
            subscriber_multiplier=50.0,
            performance_label=PerformanceLabel.BREAKOUT,
        ),
    )

    analysis_runner.return_value = SimpleNamespace(
        results=SimpleNamespace(
            considered_count=76,
            total_count=1,
            breakout_count=1,
            exceptional_performance_count=0,
            videos=(video,),
        )
    )

    response = client.post(
        "/api/analyses",
        json={
            "niche": "Marvel",
            "queries": [
                "Marvel",
                "MCU theories",
                "Marvel casting news",
                "Avengers analysis",
                "Marvel character stories",
            ],
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["niche"] == "Marvel"
    assert payload["videos_considered"] == 76
    assert payload["videos_returned"] == 1
    assert payload["breakout_count"] == 1
    assert (
        payload["exceptional_performance_count"]
        == 0
    )

    assert payload["videos"][0]["video_id"] == (
        "video-123"
    )
    assert payload["videos"][0]["views"] == 250_000
    assert payload["videos"][0]["views_per_day"] == (
        125_000.0
    )
    assert payload["videos"][0]["performance"] == (
        "breakout"
    )

    analysis_runner.assert_called_once()

    submitted_request = (
        analysis_runner.call_args.args[0]
    )

    assert submitted_request.niche == "Marvel"
    assert submitted_request.queries == [
        "Marvel",
        "MCU theories",
        "Marvel casting news",
        "Avengers analysis",
        "Marvel character stories",
    ]


def test_analysis_endpoint_rejects_duplicate_queries(
    client: TestClient,
    analysis_runner: Mock,
) -> None:
    """The endpoint should require five unique queries."""

    response = client.post(
        "/api/analyses",
        json={
            "niche": "Marvel",
            "queries": [
                "Marvel",
                "Marvel",
                "Marvel",
                "Marvel",
                "Marvel",
            ],
        },
    )

    assert response.status_code == 422
    analysis_runner.assert_not_called()


def test_analysis_endpoint_handles_runner_failure(
    client: TestClient,
    analysis_runner: Mock,
) -> None:
    """A pipeline failure should become a controlled response."""

    analysis_runner.side_effect = RuntimeError(
        "YouTube request failed."
    )

    response = client.post(
        "/api/analyses",
        json={
            "niche": "Marvel",
            "queries": [
                "Marvel",
                "MCU theories",
                "Marvel casting news",
                "Avengers analysis",
                "Marvel character stories",
            ],
        },
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": (
            "Could not complete the YouTube "
            "analysis right now."
        ),
    }