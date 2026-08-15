"""Tests for the NicheRadar HTTP API."""

from fastapi.testclient import TestClient

from nicheradar.api import app


client = TestClient(app)


def test_health_check_returns_ok() -> None:
    """The health endpoint should confirm that the API is running."""

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
    }


def test_frontend_homepage_is_served() -> None:
    """The API server should serve the NicheRadar homepage."""

    response = client.get("/")

    assert response.status_code == 200
    assert "NicheRadar" in response.text


def test_frontend_assets_are_served() -> None:
    """The browser should be able to load the CSS and JavaScript files."""

    css_response = client.get("/styles.css")
    javascript_response = client.get("/app.js")

    assert css_response.status_code == 200
    assert javascript_response.status_code == 200