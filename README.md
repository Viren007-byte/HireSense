# HireSense — React + FastAPI Recruitment Platform

A runnable portfolio application for skills-based resume screening, with React frontend and Python FastAPI backend. **This is a transparent keyword-matching baseline, not a trained AI model.** Scores are not hiring decisions; always use human review. Uses SQLite by default so you can run it quickly, with optional PostgreSQL support.

## Features
- Recruiter registration/login with hashed passwords and JWT
- Authenticated job creation, listing, deletion
- Resume uploads (PDF/DOCX/TXT, 2 MB limit)
- Extracted text and explainable skill-overlap percentage
- Candidate ranking, matched/missing skills, status workflow
- Overview dashboard with candidate counts and average match
- API docs at `/docs`; basic pytest checks
- Modern responsive React dashboard

## Run on Windows (two terminals)

**Terminal 1 — backend**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

**Terminal 2 — frontend**
```powershell
cd frontend
npm ci
npm run dev
```
Open http://localhost:5173 and sign in with the local demo account:

- Email: `demo@hiresense.local`
- Password: `HireSenseDemo123!`

The seed command creates 3 job openings and 8 fictional candidates with varied scores and statuses. Run it from `backend` after installing dependencies. Running it again preserves the existing demo account and its data, including any edits or deletions. It does not change other accounts. Demo data is only visible when signed in to the demo account; newly registered accounts start empty.

For a personal workspace, register your own account, create a job with skills `python, fastapi, sql, docker`, then upload `backend/sample_resume.txt`. Demo credentials are for local development only; do not seed a public or production database.

Backend Swagger docs: http://localhost:8000/docs

The backend reads environment variables from the shell; `.env.example` documents them and is not loaded automatically. For example, set `$env:SECRET_KEY = "your-long-random-secret"` before starting the API. To change the frontend API URL, copy `frontend/.env.example` to `frontend/.env` and edit `VITE_API_URL`.

If PowerShell blocks npm scripts, use `npm.cmd ci` and `npm.cmd run dev`.

## Run tests
```powershell
cd backend
python -m pytest -q
```

Tests use an isolated in-memory database and cover authentication, account isolation, resume uploads, scoring, workflow changes, and deletion.

Build the frontend from `frontend` with `npm run build`.

## Optional PostgreSQL

Install the optional driver from the backend environment with `pip install "psycopg[binary]>=3,<4"`.

Install PostgreSQL, create a database and user, set `DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/dbname` in your shell (or use your environment manager), and restart backend. SQLAlchemy creates the tables on startup. For production, use Alembic migrations.

## Security and limitations
- Never upload real private resumes to a public demo; use synthetic sample data.
- The default `SECRET_KEY` is **development only**. Set a strong environment secret before deploying.
- Files are parsed in memory and extracted text is stored in the database. For production add deletion/retention policy, malware scanning, stricter upload validation, rate limits, HTTPS, migrations, audit logs, and a privacy notice.
- Skill matching uses case-insensitive literal phrase matches and can miss synonyms/context. Do not treat score as suitability, ability, or a hiring recommendation.
- Frontend token uses sessionStorage for local demo; a production app should evaluate secure cookie-based auth and CSRF protection.

## Architecture
React (Vite) -> FastAPI REST -> SQLAlchemy -> SQLite (default) / PostgreSQL (optional)

## API endpoints
- `POST /auth/register`, `POST /auth/login`
- `GET /jobs`, `POST /jobs`, `DELETE /jobs/{id}`
- `POST /candidates/upload`, `GET /candidates`, `PATCH /candidates/{id}`
- `GET /analytics`, `GET /health`

## Design choices

SQLite keeps local setup small; each recruiter's jobs and candidates are scoped to their account. The React client uses the FastAPI REST API and stores the access token only for the browser session.

Matching is deterministic: matched required skills divided by total required skills, multiplied by 100. A resume mentioning Python and SQL against Python, SQL, and Docker scores 66.67%. This makes each score explainable, but cannot assess experience, skill depth, or suitability.

## Before sharing on GitHub

Publish this project directory with the README, frontend lockfile, source, and tests. The `.gitignore` excludes local environments, dependencies, generated builds, secrets, and SQLite data. A fresh clone needs `python -m app.seed` to recreate the demo workspace.

This is a local portfolio MVP. Password recovery, pagination, database migrations, and production deployment automation are not implemented.
