"""Smoke tests for the NicheRadar Streamlit interface."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "nicheradar"
    / "streamlit_app.py"
)


def test_streamlit_app_renders_initial_state() -> None:
    """The initial page should render without crashing."""

    app = AppTest.from_file(str(APP_PATH)).run()

    assert len(app.exception) == 0
    assert app.title[0].value == "NicheRadar"

    assert (
        app.text_input[0].label
        == "What niche do you want to analyse?"
    )

    assert (
        app.button[0].label
        == "Generate search queries"
    )