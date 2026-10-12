# Macro Trading Journal

One website where traders can research macroeconomic conditions, record trades and their reasoning,
track portfolio performance, and share read-only class reports with a professor.

> **Status:** early development (local only). See [docs/PROGRESS.md](docs/PROGRESS.md).

## Architecture

```
 Browser (React + TypeScript, Vite dev server :5173)
        │  fetch("/api/...")  — JSON over HTTP
        ▼
 Vite proxy ──► FastAPI backend (:8000)  ──►  PostgreSQL 18 (:5432)
                       │
                       └──► free data providers (FRED, BLS, …) — backend only, cached
```

- **frontend/** — React UI. Talks only to our backend, never to data providers directly.
- **backend/** — FastAPI. Validation, permissions, calculations, database access.
  - `app/api/` HTTP endpoints (thin) · `app/models/` database tables (SQLAlchemy) ·
    `app/db.py` connection/session · `alembic/versions/` migrations ·
    `app/domain/` pure calculations (planned) · `app/services/` glue (planned)

| Layer | Choice | Why |
|---|---|---|
| UI | React 19 + TypeScript + Vite | Component-based UI with type checking |
| Styling | Tailwind CSS v4 | Utility classes, easy responsive layouts |
| Server state | TanStack Query | Loading / error / caching for every request |
| Charts | Recharts (planned) | Simple React charts for equity/drawdown |
| API | FastAPI + Pydantic | Automatic validation and interactive docs at `/docs` |
| Database | PostgreSQL 18 + SQLAlchemy 2.1 + Alembic | Relational data + versioned migrations |

## Setup (macOS)

Requirements: Python 3.12+, Node 20+, Homebrew.

### 1. PostgreSQL

```bash
brew install postgresql@18
brew services start postgresql@18          # runs in the background and at login
```

Create a database user and two databases (dev + tests). Pick your own password:

```bash
/opt/homebrew/opt/postgresql@18/bin/psql -h localhost -d postgres
```
```sql
CREATE ROLE macro_journal WITH LOGIN PASSWORD 'choose-a-password';
CREATE DATABASE macro_journal OWNER macro_journal;
CREATE DATABASE macro_journal_test OWNER macro_journal;
\q
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then replace CHANGE_ME with your password
.venv/bin/alembic upgrade head  # create the tables
```

### 3. Frontend

```bash
cd frontend
npm install
```

## Run

Two terminals:

```bash
# Terminal 1 — backend on http://127.0.0.1:8000  (API docs at /docs)
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000
```

```bash
# Terminal 2 — frontend on http://localhost:5173
cd frontend && npm run dev
```

## Database commands

```bash
cd backend
.venv/bin/alembic upgrade head                              # apply all migrations
.venv/bin/alembic current                                   # which migration the DB is at
.venv/bin/alembic revision --autogenerate -m "describe change"  # after editing a model
.venv/bin/alembic downgrade -1                              # undo the latest migration
```

Stop / start PostgreSQL: `brew services stop postgresql@18` / `brew services start postgresql@18`.

## Checks

```bash
cd backend && .venv/bin/python -m pytest -q    # needs PostgreSQL running; uses macro_journal_test
cd frontend && npm run build && npm run lint
```

## Data sources

No external data sources are integrated yet. Each source will be verified against its official
documentation (free access, API key, rate limits, delay, licensing / redistribution) before use.

| Source | Data | Key needed | Limits | Delay | Redistribution | Status |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | none yet |

## Roadmap

1. ✅ Inspect folder, architecture
2. ✅ Frontend + backend skeleton, first API request
3. ✅ PostgreSQL + migrations
4. Journal for a local development user
5. Risk and P&L calculations (tested)
6. Secure accounts and ownership
7. Strategies, filtering, analytics
8. CSV and PDF class reports
9. Scoped, revocable share links
10. Verified free economic data sources
11. More market data + market context on trades
12. Deployment instructions
