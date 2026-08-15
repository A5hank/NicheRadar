# NicheRadar

NicheRadar is a metadata-only YouTube Shorts niche intelligence engine.

In a time where AI generated youtube channels are exploding into the scene, this will help you find the perfect niche for your AI Automation Channel, which is especially important with the YouTube monetisation changes

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

## Current status

Phase 1: Project foundation.

## Planned stack

- Python 3.13.7
- YouTube Data API v3
- SQLite and PostgreSQL
- SQLAlchemy
- Pandas, NumPy, and scikit-learn
- Sentence Transformers
- Groq API
- FastAPI with a plan HTML, CSS and JavaScript frontend

## Development setup

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```
