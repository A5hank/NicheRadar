# NicheRadar

NicheRadar is a metadata-only research tool for exploring a YouTube Shorts niche before creating content in it.

You enter a niche, such as `AI productivity`. NicheRadar suggests focused search queries, lets you review them, collects recent public YouTube metadata, and returns a ranked set of short-video candidates with transparent performance signals.

## What the application does today

- Generates up to ten focused search queries with Groq, including the original niche.
- Lets the user edit, remove, add, and approve those queries in the browser.
- Warns when a manually changed query may not be relevant to the original niche.
- Searches YouTube for recent short-duration video candidates published during the last seven days.
- Fetches public video and channel metadata, removes duplicates, and stores observations in SQLite by default.
- Calculates views per day, subscriber multiplier, breakout and exceptional-performance labels, a Virality Score, and a Confidence Score.
- Shows up to 50 selected candidates in the browser, displayed in views-per-day order.

The final result set is selected by total views first, then ranked for display by views per day. This is deliberate: it keeps the dashboard focused on well-viewed candidates while still making upload-age-adjusted performance easy to compare.

## Scope and current limitations

NicheRadar analyses public metadata only. It does not download or analyse video frames, audio, or transcripts.

The tool uses a duration-based definition of a Short candidate: a recent YouTube search result that is no longer than 180 seconds. It does not receive a definitive `is_short` flag from YouTube.

The application stores daily niche snapshots and calculates like, comment, and engagement rates internally. It does not yet show historical trends or engagement-rate values in the browser. Groq is used for query suggestions and query-relevance warnings; it does not currently write a final AI narrative explaining the analysis.

NicheRadar is a research aid, not a guarantee that a niche or video will succeed. It is not affiliated with YouTube.

## How it works

```text
Browser
  -> Groq: query suggestions and optional relevance check
  -> YouTube Data API: recent video and channel metadata
  -> SQLite / SQLAlchemy: persist observations and daily snapshots
  -> Analytics: score, select, and rank candidates
  -> Browser dashboard: results and transparent scores
```

For each approved query, the backend asks YouTube for up to 50 recent results, deduplicates the collected videos, filters them to Short candidates, and retrieves channel metadata. It then calculates the performance signals and returns the final dashboard response.

## Technology

- Python 3.13
- FastAPI and Uvicorn
- YouTube Data API v3
- Groq Chat Completions API
- SQLAlchemy with SQLite by default
- Plain HTML, CSS, and JavaScript frontend
- Podman/Docker-compatible container configuration

## Requirements

- Python 3.13.7 is recommended; the project accepts Python 3.13.x.
- A YouTube Data API key.
- A Groq API key.

## Local setup

From the project root in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Open `.env` and add your keys:

```dotenv
YOUTUBE_API_KEY=your_youtube_key
GROQ_API_KEY=your_groq_key
DATABASE_URL=sqlite:///data/nicheradar.db
APP_ENV=development
```

Do not commit `.env`; it is already ignored by Git.

## Run the web application

Start FastAPI from the project root:

```powershell
python -m uvicorn nicheradar.api:app --reload
```

Then open:

- Application: <http://127.0.0.1:8000>
- Interactive API documentation: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/api/health>

The frontend must be served by this FastAPI application for live analysis to work. A standalone `python -m http.server` can display the files, but it does not provide the required `/api/...` endpoints.

## Run a command-line analysis

The command-line workflow uses the same Groq query expansion and YouTube analysis pipeline, then prompts you to review the generated queries:

```powershell
python -m nicheradar.analyze "AI productivity"
```

Optional limits are available from 1 to 50:

```powershell
python -m nicheradar.analyze "AI productivity" --search-limit 50 --result-limit 50
```

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Confirms that the application is running. |
| `POST` | `/api/queries` | Generates focused search queries for a niche. |
| `POST` | `/api/query-relevance` | Checks manually changed queries for relevance. |
| `POST` | `/api/analyses` | Collects metadata and returns a complete niche analysis. |

## Project layout

```text
frontend/                 Browser interface and About page
src/nicheradar/           Application, API, collection, storage, and analytics code
tests/                    Automated unit and API tests
data/                     Local SQLite database location (ignored except .gitkeep)
Containerfile             Runtime image definition
compose.yaml              Local container service definition
```

## Run checks

```powershell
pytest -q
ruff check .
```

## Run with containers

Create `.env` as described above, then run:

```powershell
podman compose up --build
```

The compose file exposes the application only on `127.0.0.1:8000` and persists SQLite data in the `nicheradar-data` volume.
