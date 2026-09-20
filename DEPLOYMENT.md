# Private Vercel staging

NicheRadar is deployed to Vercel only as a private, owner-controlled staging
environment. It is not a public interactive real-data service. The public
repository is intended for portfolio source review; credentials, database
data, and deployment secrets remain private.

## Local development

Keep SQLite for local development:

```dotenv
DATABASE_URL=sqlite:///data/nicheradar.db
APP_ENV=development
APP_MODE=local
```

Initialize or upgrade the local database before starting the server:

```powershell
.\.venv\Scripts\Activate.ps1
python -m nicheradar.init_db
python -m uvicorn nicheradar.api:app --reload
```

## Required Preview environment variables

Set these only in Vercel Project Settings. Never put their values in browser
code, committed files, logs, test fixtures, screenshots, or public documents.

```dotenv
DATABASE_URL=postgresql+psycopg://...
YOUTUBE_API_KEY=...
GROQ_API_KEY=...
APP_ENV=production
APP_MODE=private_staging
CRON_SECRET=a-long-random-secret
```

The default daily YouTube search budget is 80. Adjust this only after checking
the actual quota in the Google Cloud project:

```dotenv
YOUTUBE_DAILY_SEARCH_BUDGET=80
```

Optional conservative runtime controls are:

```dotenv
ANALYSIS_TIMEOUT_SECONDS=45
YOUTUBE_TIMEOUT_SECONDS=8
GROQ_TIMEOUT_SECONDS=10
RATE_LIMIT_PER_MINUTE=10
ANALYSIS_RATE_LIMIT_PER_MINUTE=2
```

## Initial staging setup

Install the Vercel CLI, link the repository to the Vercel project, and set the
variables above for the Preview environment. Do not run the migration until a
managed PostgreSQL database exists.

```powershell
npm install --global vercel
vercel login
vercel link
vercel env add DATABASE_URL preview
vercel env add YOUTUBE_API_KEY preview
vercel env add GROQ_API_KEY preview
vercel env add APP_ENV preview
vercel env add APP_MODE preview
vercel env add CRON_SECRET preview
vercel env add YOUTUBE_DAILY_SEARCH_BUDGET preview
```

Pull Preview variables into an ignored temporary file and run the migration
against PostgreSQL before the first staging deployment:

```powershell
vercel env pull .env.vercel.preview --environment=preview
Get-Content .env.vercel.preview | ForEach-Object {
  if ($_ -match '^(?<name>[^=]+)=(?<value>.*)$') {
    Set-Item -Path "Env:$($matches.name)" -Value $matches.value
  }
}
python -m nicheradar.init_db
Remove-Item .env.vercel.preview
```

Create a Preview deployment:

```powershell
vercel deploy --yes
```

Do not run `vercel --prod` for the current portfolio staging workflow.

## Staging safeguards

- Each analysis is isolated by an immutable run ID; same-niche same-day runs
  cannot share result rows.
- The server reserves the approved-query count from a durable UTC daily
  YouTube search budget before contacting YouTube.
- Per-client rate limits and duplicate in-flight analysis locks are stored in
  PostgreSQL, so they work across Vercel function instances.
- A 45-second server deadline intentionally finishes before the configured
  60-second function duration.
- The daily Vercel Cron calls the protected retention endpoint. Analysis runs
  and their public YouTube metadata expire within 30 days.
- A `429` response means temporary request throttling or exhausted daily
  analysis capacity; it does not reveal provider details.

## Before any public real-data release

- Complete a real PostgreSQL integration test. Local tests use SQLite; the
  managed database is validated by staging migration and smoke testing.
- Restrict the Google API key to YouTube Data API usage. Do not expose it in
  the frontend.
- Check Groq project limits and set a conservative project limit.
- Complete YouTube API compliance and derived-metrics review before allowing
  public real-data analysis.
- Add final attribution, Terms, Privacy Policy, consent, and a contact/deletion
  path before opening a public service.
