# Macro Trading Journal

One website where traders can research macroeconomic conditions, record trades and their reasoning,
track portfolio performance, and share read-only class reports with a professor.

> **Status:** early development (local only). See [docs/PROGRESS.md](docs/PROGRESS.md).

## Architecture

```
 Browser (React + TypeScript, Vite dev server :5173)
        │  fetch("/api/...")  — JSON over HTTP
        ▼
 Vite proxy ──► FastAPI backend (:8000)  ──►  PostgreSQL  (from Milestone 3)
                       │
                       └──► free data providers (FRED, BLS, …) — backend only, cached
```

- **frontend/** — React UI. Talks only to our backend, never to data providers directly.
- **backend/** — FastAPI. Validation, permissions, calculations, database access.
  - `app/api/` HTTP endpoints (thin) · `app/domain/` pure calculations (planned) ·
    `app/models/` database tables (planned) · `app/services/` glue (planned)

| Layer | Choice | Why |
|---|---|---|
| UI | React 19 + TypeScript + Vite | Component-based UI with type checking |
| Styling | Tailwind CSS v4 | Utility classes, easy responsive layouts |
| Server state | TanStack Query | Loading / error / caching for every request |
| Charts | Recharts (planned) | Simple React charts for equity/drawdown |
| API | FastAPI + Pydantic | Automatic validation and interactive docs at `/docs` |
| Database | PostgreSQL + SQLAlchemy 2 + Alembic (planned) | Relational data + versioned migrations |

## Setup (macOS)

Requirements: Python 3.12+, Node 20+.

```bash
# Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env

# Frontend
cd ../frontend
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

## Checks

```bash
cd backend && .venv/bin/python -m pytest -q
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
2. ⏳ Frontend + backend skeleton, first API request
3. PostgreSQL + migrations
4. Journal for a local development user
5. Risk and P&L calculations (tested)
6. Secure accounts and ownership
7. Strategies, filtering, analytics
8. CSV and PDF class reports
9. Scoped, revocable share links
10. Verified free economic data sources
11. More market data + market context on trades
12. Deployment instructions
