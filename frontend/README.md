# NicheRadar frontend prototype

This is the first framework-free frontend checkpoint for NicheRadar.

It currently uses sample queries, counts, and video rows so the complete user
flow can be reviewed before connecting the existing Python backend.

## Run locally

From this directory:

```powershell
python -m http.server 8000
```

Then open `http://localhost:8000` in your browser.

## Current behavior

- Enter submits the landing-page search form.
- An empty niche displays a validation error.
- A valid niche opens a query-review screen with ten suggested searches.
- Queries can be edited, removed, and added; analysis stays disabled until between one and ten non-empty, unique queries are approved.
- Approving the queries switches to the results dashboard.
- Breakout rows use `#78C0A8`.
- Exceptional-performance rows use `#6B8CCE`.
- New analysis returns to the landing page.

## Next backend checkpoint

The next step is to add a FastAPI application with JSON endpoints for query
generation and complete niche analysis. `app.js` will then replace the sample
arrays with `fetch()` calls to those endpoints.
