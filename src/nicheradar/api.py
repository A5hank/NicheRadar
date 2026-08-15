"""HTTP API and frontend server for NicheRadar."""

from pathlib import Path

from fastapi import FastAPI


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIRECTORY = PROJECT_ROOT / "frontend"

if not FRONTEND_DIRECTORY.is_dir():
    raise RuntimeError(
        f"Frontend directory does not exist: {FRONTEND_DIRECTORY}"
    )


app = FastAPI(
    title="NicheRadar API",
    version="0.1.0",
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


app.frontend(
    "/",
    directory=str(FRONTEND_DIRECTORY),
)