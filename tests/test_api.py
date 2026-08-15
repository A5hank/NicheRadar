"""Tests for the NicheRadar HTTP API."""

from collections.abc import Iterator
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from nicheradar.api import (
    app,
    get_groq_client,
)
from nicheradar.groq_client import (
    GroqAPIError,
    GroqClient,
)


@pytest.fixture
def groq_client() -> Mock:
    """Create a fake Groq client that never makes network requests."""

    return Mock(spec=GroqClient)


@pytest.fixture
def client(
    groq_client: Mock,
) -> Iterator[TestClient]:
    """Create an API client using the fake Groq dependency."""

    def override_groq_client() -> Iterator[Mock]:
        yield groq_client

    app.dependency_overrides[get_groq_client] = (
        override_groq_client
    )

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_health_check_returns_ok(
    client: TestClient,
) -> None:
    """The health endpoint should confirm that the API is running."""

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
    }


def test_frontend_homepage_is_served(
    client: TestClient,
) -> None:
    """The API server should serve the NicheRadar homepage."""

    response = client.get("/")

    assert response.status_code == 200
    assert "NicheRadar" in response.text


def test_frontend_assets_are_served(
    client: TestClient,
) -> None:
    """The browser should be able to load the frontend assets."""

    css_response = client.get("/styles.css")
    javascript_response = client.get("/app.js")

    assert css_response.status_code == 200
    assert javascript_response.status_code == 200


def test_query_endpoint_returns_expanded_queries(
    client: TestClient,
    groq_client: Mock,
) -> None:
    """The endpoint should return validated Groq suggestions."""

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
    """The endpoint should reject whitespace-only niches."""

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
    """A Groq failure should become a controlled API response."""

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
        "detail": "Could not generate search queries right now.",
    }