# Progress Checklist

Legend: ✅ done · ⏳ in progress · ⬜ not started

## Phase 1 — Inspect & plan
- ✅ Inspected machine: Node 26, Python 3.12, Homebrew, Git; no PostgreSQL / Docker
- ✅ Architecture and technology choices agreed

## Phase 2 — Frontend + backend skeleton
- ✅ **2a** FastAPI app with `GET /api/health`, Vite React TS app with Tailwind + TanStack Query,
  Vite proxy, loading/error/success states, pytest for health endpoint
- ⬜ 2b (optional) app layout shell: navigation for Journal / Analytics / Dashboard / Reports

## Phase 3 — PostgreSQL + migrations
- ✅ PostgreSQL 18 via Homebrew (`brew services`), role `macro_journal`,
  databases `macro_journal` (dev) and `macro_journal_test` (tests)
- ✅ SQLAlchemy engine/session (`app/db.py`), `Base` with naming conventions
- ✅ Alembic configured to read the URL from `.env`; migration 001 creates `users`
- ✅ Health endpoint + UI report database connected / unavailable
- ✅ Tests rebuild the test DB from migrations and roll back each test (5 passing)

## Phase 4 — Journal (local dev user)
- ⬜ Portfolios, instruments (stocks + futures metadata), trades, executions
- ⬜ CRUD endpoints + journal UI

## Phase 5 — Risk & P&L calculations
## Phase 6 — Accounts & ownership
## Phase 7 — Strategies, filtering, analytics
## Phase 8 — CSV / PDF reports
## Phase 9 — Share links
## Phase 10 — Free economic data
## Phase 11 — Market data + trade context
## Phase 12 — Deployment plan

## How to resume
1. Read this file and `docs/LEARNING_NOTES.md`.
2. Start backend + frontend (see README "Run").
3. Continue with the first ⬜ item.
