"""Tests for the Vercel serverless-function entrypoint."""

import importlib.util
from pathlib import Path

from nicheradar.api import app as nicheradar_app


def test_vercel_entrypoint_exports_the_existing_fastapi_app() -> None:
    """Vercel should serve the same app used by local development."""

    project_root = Path(__file__).resolve().parents[1]
    entrypoint_path = project_root / "api" / "index.py"
    module_specification = importlib.util.spec_from_file_location(
        "nicheradar_vercel_entrypoint",
        entrypoint_path,
    )

    assert module_specification is not None
    assert module_specification.loader is not None

    module = importlib.util.module_from_spec(module_specification)
    module_specification.loader.exec_module(module)

    assert module.app is nicheradar_app
