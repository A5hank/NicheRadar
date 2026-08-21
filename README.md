# NicheRadar

NicheRadar is a metadata-only YouTube Shorts niche intelligence engine.

In a time where AI generated youtube channels are exploding into the scene, this will help you find the perfect niche for your AI Automation Channel, which is especially important with the YouTube monetisation changes.

Given a niche such as `AI productivity`, it will identify:

- Top-performing Shorts from the last seven days
- Small creators outperforming their subscriber count
- Emerging topics within the niche
- Performance and engagement trends
- AI-generated explanations based on structured analytics

## Project principle

NicheRadar analyzes publicly available metadata only.

It does not analyze:
- Video frames
- Audio
- Transcripts

This keeps the system cheaper, faster, and focused on performance intelligence.

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

## Run with containers

Create `.env` as described above, then run:

```powershell
podman compose up --build
```

The compose file exposes the application only on `127.0.0.1:8000` and persists SQLite data in the `nicheradar-data` volume.

## Roadmap (What's Next)

NicheRadar v0.9.0 is currently a "Phase One" milestone. Planned improvements include:

- **Historical Trend Analysis:** Transitioning from daily snapshots to visualizing engagement rate trends over time.
- **AI Narrative Generation:** Expanding the Groq integration to write a final, comprehensive analytical report based on the collected SQLite data.
- **Enhanced Data Pipeline:** Adding PostgreSQL support for heavier workloads and caching to reduce redundant YouTube API calls.
- **UI/UX Polish:** Adding interactive charts for view-velocity and better mobile responsiveness.
