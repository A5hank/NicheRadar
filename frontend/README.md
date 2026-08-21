# NicheRadar frontend

This is NicheRadar's framework-free browser interface. FastAPI serves this directory at `/`, and `app.js` communicates with the backend using JSON requests.

## Run it locally

Run the application from the project root, not from this directory:

```powershell
python -m uvicorn nicheradar.api:app --reload
```

Open <http://127.0.0.1:8000>.

Do not use `python -m http.server` when testing the complete application. It can serve the static files, but it cannot provide the FastAPI endpoints that the interface calls.

## Current behavior

- The landing form validates the entered niche and requests Groq-generated query suggestions from `POST /api/queries`.
- The query-review screen starts with up to ten queries, including the original niche as the locked first query.
- The user can edit, remove, or add queries. Between one and ten unique, non-empty queries are required.
- Manually changed queries are checked through `POST /api/query-relevance`; the user can return to editing or continue after a warning.
- Approved queries start the real YouTube collection and analysis through `POST /api/analyses`.
- The dashboard renders returned videos, breakout and exceptional-performance counts, Virality Score, and Confidence Score.
- The theme toggle stores the selected light or dark theme in browser local storage.
- Starting a new analysis returns to the landing screen.

## Main files

| File | Role |
| --- | --- |
| `index.html` | Landing, query-review, warning dialog, and results-dashboard markup. |
| `app.js` | Browser state, validation, API requests, and dynamic rendering. |
| `styles.css` | Application layout, colours, responsive styling, and theme rules. |
| `about.html` | The standalone About page served at `/about`. |
| `about.js` / `about.css` | About-page interactions and styling. |

The browser never receives the Groq or YouTube API keys; those remain in the Python backend.
