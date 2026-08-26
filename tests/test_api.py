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

    app.dependency_overrides[get_groq_client] = override_groq_client
    app.dependency_overrides[get_analysis_runner] = override_analysis_runner

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
    assert 'href="/about"' in response.text


def test_frontend_assets_are_served(
    client: TestClient,
) -> None:
    """The browser should be able to load frontend assets."""

    css_response = client.get("/styles.css")
    ranking_javascript_response = client.get("/result-ranking.js")
    javascript_response = client.get("/app.js")
    logo_response = client.get("/assets/nicheradar-mark.svg")
    about_css_response = client.get("/about.css")
    about_javascript_response = client.get("/about.js")

    assert css_response.status_code == 200
    assert ranking_javascript_response.status_code == 200
    assert javascript_response.status_code == 200
    assert logo_response.status_code == 200
    assert about_css_response.status_code == 200
    assert about_javascript_response.status_code == 200

    assert logo_response.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in logo_response.content


def test_about_page_is_served(
    client: TestClient,
) -> None:
    """The browser should receive the dedicated About page."""

    response = client.get("/about")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")

    assert "<title>About NicheRadar</title>" in response.text
    assert 'href="/about.css"' in response.text
    assert 'src="/about.js"' in response.text

    assert "https://github.com/A5hank" in response.text
    assert "https://www.linkedin.com/in/ashank-kumar-singh/" in response.text


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


def test_analysis_request_accepts_ten_queries() -> None:
    """The API should accept the maximum of ten queries."""

    queries = ["Marvel"]

    queries.extend(f"Marvel angle {index}" for index in range(1, 10))

    request = AnalysisRequest(
        niche="Marvel",
        queries=queries,
    )

    assert request.queries == queries


def test_analysis_request_rejects_more_than_ten_queries() -> None:
    """The API must reject an eleventh query."""

    queries = ["Marvel"]

    queries.extend(f"Marvel angle {index}" for index in range(1, 11))

    with pytest.raises(ValueError):
        AnalysisRequest(
            niche="Marvel",
            queries=queries,
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
            "Marvel comics explained",
            "Marvel movie breakdowns",
            "Marvel villain origins",
            "Marvel fan theories",
            "Marvel timeline",
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
            "Marvel comics explained",
            "Marvel movie breakdowns",
            "Marvel villain origins",
            "Marvel fan theories",
            "Marvel timeline",
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

    groq_client.generate_json.side_effect = GroqAPIError("Could not connect to the Groq API.")

    response = client.post(
        "/api/queries",
        json={
            "niche": "Marvel",
        },
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": ("Could not generate search queries right now."),
    }


def test_query_relevance_endpoint_returns_warnings(
    client: TestClient,
    groq_client: Mock,
) -> None:
    """Clearly unrelated queries should produce warnings."""

    groq_client.generate_json.return_value = {
        "assessments": [
            {
                "index": 0,
                "is_relevant": True,
                "reason": ("Home workouts are directly related to gym content."),
            },
            {
                "index": 1,
                "is_relevant": False,
                "reason": ("Minecraft survival is not related to gym content."),
            },
        ]
    }

    response = client.post(
        "/api/query-relevance",
        json={
            "niche": "  Gym  ",
            "queries": [
                " Home workout routines ",
                " Minecraft survival ",
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "niche": "Gym",
        "warnings": [
            {
                "query": "Minecraft survival",
                "reason": ("Minecraft survival is not related to gym content."),
            }
        ],
    }

    groq_client.generate_json.assert_called_once()


def test_query_relevance_endpoint_accepts_related_queries(
    client: TestClient,
    groq_client: Mock,
) -> None:
    """Related manually changed queries need no warning."""

    groq_client.generate_json.return_value = {
        "assessments": [
            {
                "index": 0,
                "is_relevant": True,
                "reason": ("Workout motivation is a useful gym content angle."),
            }
        ]
    }

    response = client.post(
        "/api/query-relevance",
        json={
            "niche": "Gym",
            "queries": [
                "Workout motivation",
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "niche": "Gym",
        "warnings": [],
    }

    groq_client.generate_json.assert_called_once()


def test_query_relevance_endpoint_rejects_more_than_nine_queries(
    client: TestClient,
    groq_client: Mock,
) -> None:
    """The API should reject ten non-original queries."""

    response = client.post(
        "/api/query-relevance",
        json={
            "niche": "Gym",
            "queries": [f"Query {index}" for index in range(1, 11)],
        },
    )

    assert response.status_code == 422
    groq_client.generate_json.assert_not_called()


def test_query_relevance_endpoint_handles_invalid_groq_data(
    client: TestClient,
    groq_client: Mock,
) -> None:
    """Malformed relevance output should become a safe response."""

    groq_client.generate_json.return_value = {
        "unexpected": [],
    }

    response = client.post(
        "/api/query-relevance",
        json={
            "niche": "Gym",
            "queries": [
                "Minecraft survival",
            ],
        },
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": ("Could not verify query relevance right now."),
    }


def test_analysis_endpoint_returns_dashboard_data(
    client: TestClient,
    analysis_runner: Mock,
) -> None:
    """The endpoint should serialize complete analysis data."""

    video = SimpleNamespace(
        video_id="video-123",
        channel_id="channel-123",
        title="Marvel Theory Explained",
        url="https://www.youtube.com/watch?v=video-123",
        thumbnail_url=("https://images.example/video-123-medium.jpg"),
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
                "Marvel movie breakdowns",
                "Marvel fan theories",
                "Marvel villains",
                "Marvel Easter eggs",
                "Marvel comics explained",
            ],
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["niche"] == "Marvel"
    assert payload["videos_considered"] == 76
    assert payload["videos_returned"] == 1
    assert payload["breakout_count"] == 1
    assert payload["exceptional_performance_count"] == 0

    assert payload["videos"][0]["video_id"] == ("video-123")
    assert payload["videos"][0]["thumbnail_url"] == ("https://images.example/video-123-medium.jpg")
    assert payload["videos"][0]["rank"] == 1
    assert payload["videos"][0]["views"] == 250_000
    assert payload["videos"][0]["views_per_day"] == (125_000.0)
    assert payload["videos"][0]["subscriber_multiplier"] == 50.0
    assert payload["videos"][0]["performance"] == ("breakout")

    analysis_runner.assert_called_once()

    submitted_request = analysis_runner.call_args.args[0]

    assert submitted_request.niche == "Marvel"
    assert submitted_request.queries == [
        "Marvel",
        "MCU theories",
        "Marvel casting news",
        "Avengers analysis",
        "Marvel character stories",
        "Marvel movie breakdowns",
        "Marvel fan theories",
        "Marvel villains",
        "Marvel Easter eggs",
        "Marvel comics explained",
    ]

    assert payload["virality_score"] == {
        "score": 30,
        "label": "emerging",
        "breakdown": {
            "breakout_points": 0,
            "velocity_points": 30,
            "exceptional_points": 0,
            "diversity_points": 0,
            "median_views_per_day": 125_000.0,
            "unique_channel_count": 1,
        },
    }

    assert payload["confidence_score"] == {
        "score": 70,
        "label": "good",
    }


def test_analysis_endpoint_preserves_client_side_ranking_values(
    client: TestClient,
    analysis_runner: Mock,
) -> None:
    """The browser should receive stable ranks and all local sorting metrics."""

    velocity_leader = SimpleNamespace(
        video_id="velocity-leader",
        channel_id="channel-velocity",
        title="Fast-growing Marvel theory",
        url="https://www.youtube.com/watch?v=velocity-leader",
        thumbnail_url=None,
        channel_name="Velocity Channel",
        upload_date=datetime(
            2026,
            8,
            14,
            12,
            0,
            tzinfo=UTC,
        ),
        views=150_000,
        subscribers=3_000,
        metrics=SimpleNamespace(
            views_per_day=125_000.0,
            subscriber_multiplier=50.0,
            performance_label=PerformanceLabel.BREAKOUT,
        ),
    )
    total_views_leader = SimpleNamespace(
        video_id="total-views-leader",
        channel_id="channel-total-views",
        title="Popular Marvel recap",
        url="https://www.youtube.com/watch?v=total-views-leader",
        thumbnail_url=None,
        channel_name="Total Views Channel",
        upload_date=datetime(
            2026,
            8,
            14,
            12,
            0,
            tzinfo=UTC,
        ),
        views=950_000,
        subscribers=100_000,
        metrics=SimpleNamespace(
            views_per_day=20_000.0,
            subscriber_multiplier=9.5,
            performance_label=PerformanceLabel.REGULAR,
        ),
    )
    no_subscriber_data = SimpleNamespace(
        video_id="no-subscriber-data",
        channel_id="channel-unknown",
        title="Marvel hidden channel video",
        url="https://www.youtube.com/watch?v=no-subscriber-data",
        thumbnail_url=None,
        channel_name="Unknown Subscribers Channel",
        upload_date=datetime(
            2026,
            8,
            14,
            12,
            0,
            tzinfo=UTC,
        ),
        views=400_000,
        subscribers=None,
        metrics=SimpleNamespace(
            views_per_day=10_000.0,
            subscriber_multiplier=None,
            performance_label=PerformanceLabel.REGULAR,
        ),
    )

    analysis_runner.return_value = SimpleNamespace(
        results=SimpleNamespace(
            considered_count=3,
            total_count=3,
            breakout_count=1,
            exceptional_performance_count=0,
            videos=(
                velocity_leader,
                total_views_leader,
                no_subscriber_data,
            ),
        )
    )

    response = client.post(
        "/api/analyses",
        json={
            "niche": "Marvel",
            "queries": [
                "Marvel",
                "MCU theories",
            ],
        },
    )

    assert response.status_code == 200
    assert [
        {
            "rank": video["rank"],
            "views": video["views"],
            "views_per_day": video["views_per_day"],
            "subscriber_multiplier": video["subscriber_multiplier"],
        }
        for video in response.json()["videos"]
    ] == [
        {
            "rank": 1,
            "views": 150_000,
            "views_per_day": 125_000.0,
            "subscriber_multiplier": 50.0,
        },
        {
            "rank": 2,
            "views": 950_000,
            "views_per_day": 20_000.0,
            "subscriber_multiplier": 9.5,
        },
        {
            "rank": 3,
            "views": 400_000,
            "views_per_day": 10_000.0,
            "subscriber_multiplier": None,
        },
    ]


def test_analysis_endpoint_rejects_duplicate_queries(
    client: TestClient,
    analysis_runner: Mock,
) -> None:
    """Every submitted query should be unique."""

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

    analysis_runner.side_effect = RuntimeError("YouTube request failed.")

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
        "detail": ("Could not complete the YouTube analysis right now."),
    }
