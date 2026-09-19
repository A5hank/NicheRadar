"""Catch-all Vercel Function entrypoint for FastAPI API routes."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = PROJECT_ROOT / "src"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIRECTORY))

from nicheradar.api import app  # noqa: E402

__all__ = ["app"]
