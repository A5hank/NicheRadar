# Public limited-beta deployment

This repository is prepared for a later Vercel deployment, but this document
does not deploy the application or create any remote repositories.

## Local development

Keep SQLite for local development:

```dotenv
DATABASE_URL=sqlite:///data/nicheradar.db
APP_ENV=development
APP_MODE=local
```

After pulling the public-beta foundation, initialize or upgrade the local
database before starting the server:

```powershell
.\.venv\Scripts\Activate.ps1
python -m nicheradar.init_db
python -m uvicorn nicheradar.api:app --reload
```

## Required Vercel environment variables

Set these only in Vercel Project Settings. Never put their values in browser
code, committed files, logs, test fixtures, screenshots, or public documents.

```dotenv
DATABASE_URL=postgresql+psycopg://...
YOUTUBE_API_KEY=...
GROQ_API_KEY=...
APP_ENV=production
APP_MODE=public_beta
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

## Pre-deployment commands

Install the Vercel CLI, link the existing repository to a new Vercel project,
and set the variables above through the Vercel dashboard or CLI. Do not run
these commands until a managed PostgreSQL database exists.

```powershell
npm install --global vercel
vercel login
vercel link
vercel env add DATABASE_URL production
vercel env add YOUTUBE_API_KEY production
vercel env add GROQ_API_KEY production
vercel env add APP_ENV production
vercel env add APP_MODE production
vercel env add CRON_SECRET production
vercel env add YOUTUBE_DAILY_SEARCH_BUDGET production
```

Pull production variables into an ignored temporary file and run the migration
against PostgreSQL before the first production deployment:

```powershell
vercel env pull .env.vercel.production --environment=production
Get-Content .env.vercel.production | ForEach-Object {
  if ($_ -match '^(?<name>[^=]+)=(?<value>.*)$') {
    Set-Item -Path "Env:$($matches.name)" -Value $matches.value
  }
}
python -m nicheradar.init_db
Remove-Item .env.vercel.production
```

Then create a preview deployment first:

```powershell
vercel
```

Only after the preview checks pass should a public limited-beta deployment be
created:

```powershell
vercel --prod
```

## Behaviour in public beta

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

## Still required before broad public promotion

- Create the managed PostgreSQL database and verify it with a real integration
  test. Local tests use SQLite; PostgreSQL connectivity is not exercised here.
- Restrict the Google API key to YouTube Data API usage. Do not expose it in
  the frontend.
- Check Groq project limits and set a conservative project limit.
- Review YouTube API compliance, attribution, Terms, Privacy Policy, consent,
  and contact/deletion handling.
- Audit the existing About-page GitHub/GPL source links before making the full
  source repository private, since they currently claim that the source is
  publicly available.
