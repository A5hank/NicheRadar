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

- The landing form validates the entered niche, checks it through `POST /api/niche-spelling`, and uses one Groq web search to offer a likely search match only when confidence is high. The user must explicitly choose the suggested search or keep the original text before `POST /api/queries` generates search queries. A failed check proceeds with the original niche.
- The query-review screen starts with up to ten queries, including the original niche as the locked first query.
- The user can edit, remove, or add queries. Between one and ten unique, non-empty queries are required.
- Manually changed queries are checked through `POST /api/query-relevance`; the user can return to editing or continue after a warning.
- Approved queries start the real YouTube collection and analysis through `POST /api/analyses`.
- The dashboard renders returned videos, breakout and exceptional-performance counts, Virality Score, and Confidence Score.
- Once the deterministic dashboard is visible, `POST /api/analysis-summary` optionally adds three Groq observations and a deterministic new-creator signal. It never reruns YouTube collection; a slow or failed request shows `Summary unavailable` without affecting results.
- The result-list dropdown reorders the already returned videos by Views/day, Total views, or Subscriber multiplier without making another API request. Videos without a multiplier remain at the bottom in multiplier mode.
- The interface uses a single dark theme and includes an optional first-visit brand introduction that respects reduced-motion preferences.
- Starting a new analysis returns to the landing screen.

## Main files

| File | Role |
| --- | --- |
| `index.html` | Landing, query-review, warning dialog, and results-dashboard markup. |
| `result-ranking.js` | Pure client-side ranking helper shared by the dashboard and Node regression tests. |
| `spelling-suggestion.js` | Pure search-suggestion safety and explicit-choice helper shared by the landing page and Node regression tests. |
| `analysis-summary.js` | Pure summary-request and response-safety helper shared by the dashboard and Node regression tests. |
| `intro.js` | Dependency-free first-visit crowd animation and intro timing helper. |
| `app.js` | Browser state, validation, API requests, and dynamic rendering. |
| `styles.css` | Dark-only application layout, colours, responsive styling, and intro styling. |
| `about.html` | The standalone About page served at `/about`. |
| `about.js` / `about.css` | About-page interactions and styling. |

The browser never receives the Groq or YouTube API keys; those remain in the Python backend.

## Frontend regression test

Run the dependency-free frontend regression tests from the project root:

```powershell
node --test frontend/tests/*.test.cjs
```
