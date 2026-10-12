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
- ✅ **4a** Data model + migration 002: portfolios, cash_flows, strategies, instruments,
  futures_contracts, trades, trade_targets, executions. DB check constraints.
  11 CME futures seeded (`python -m app.seed`), verified against CME spec pages 2026-10-11.
  Local dev user `dev@localhost.test`. 30 tests passing.
- ✅ **4b** API: portfolios (CRUD), strategies (list/create), instruments + stock creation,
  futures contracts, trades (CRUD, search, filters, date range). Domain rules in
  `app/domain/trade_rules.py` (tick grid, whole contracts, stop/target side, fill order/size/time,
  derived status). Initial stop locked after entry. Ownership → 404. 78 tests passing.
- ⬜ Cash-flow (deposit/withdrawal) endpoints — with the portfolio screen
- ⬜ Editing individual executions when a trade has multiple fills (PUT returns 409 for now)
- ✅ **4c** Journal UI (React Router): Setup page (portfolios, strategies), journal list with
  search + filters in the URL (table on desktop, cards on phones), trade form (new/edit, inline
  contract + stock creation, up to 5 targets, one entry + one exit, 32nds hints, server errors shown
  per field, initial stop locked after entry), trade detail with delete. Vitest: 8 format tests.
- ⬜ Later: attachments/screenshots (needs upload validation), tags, stop-change history, options

## Phase 5 — Risk & P&L calculations
- ✅ Pure module `app/domain/calculations.py`: planned R:R per target, planned risk, initial dollar risk,
  weighted average entry/exit, gross/net realized P&L with proportional entry-fee allocation, realized R,
  unrealized P&L (requires a sourced market price), explicit "unavailable" reasons.
- ✅ 19 calculation tests (worked example, partial exit, short, scaling in, multiple exits, corn cents,
  ZN half-cent rounding, fractional shares, missing stop, unrealized) + 2 API tests. 99 backend tests total.
- ✅ Trade API returns `metrics`; journal list shows Net P&L and R; detail page has a Risk & results panel.
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
