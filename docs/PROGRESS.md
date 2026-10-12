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
- ⬜ Install PostgreSQL locally (Homebrew), create dev + test databases
- ⬜ SQLAlchemy engine/session, Alembic init, first migration

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
