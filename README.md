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
    `app/schemas/` request/response shapes · `app/services/` ownership + data access ·
    `app/domain/` pure rules and calculations (no DB, no web)

| Layer | Choice | Why |
|---|---|---|
| UI | React 19 + TypeScript + Vite | Component-based UI with type checking |
| Styling | Tailwind CSS v4 | Utility classes, easy responsive layouts |
| Server state | TanStack Query | Loading / error / caching for every request |
| Routing | React Router 8 | Pages at `/trades`, `/trades/:id`, `/trades/new`, `/setup` |
| Frontend tests | Vitest | Formatting helpers (32nds, money, time zones) |
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
.venv/bin/python -m app.seed    # load futures specs + local dev user (safe to re-run)
```

### 3. Frontend

```bash
cd frontend
npm install
```

## Using the journal

1. Open http://localhost:5173 → **Portfolios & strategies** → create a portfolio (and optionally strategies).
2. **Journal → + New trade** → pick product and contract (add a contract month with the exchange's
   last trading day the first time), plan, reasoning, and optionally the entry/exit fills.
3. Treasury futures (ZN, ZB) are typed as decimals; the form shows the 32nds quote (e.g. `112'16.5`).
4. Times are entered in your local time and stored in UTC.

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

## Data model

```
users ─┬─< portfolios ─┬─< trades >── instruments ──< futures_contracts
       │               │    │  │
       └─< strategies >┼────┘  ├──< trade_targets   (TP1, TP2, …)
                       │       └──< executions      (actual entry/exit fills)
                       └─< cash_flows (deposits / withdrawals — never counted as P&L)
```

- Prices are stored in the exchange's **quoted unit** (ES in index points, ZC in US cents per bushel).
  `instruments.point_value` = USD per 1.0 move in that quote, per contract/share.
- `trades.initial_stop_price` is preserved; later stop changes go in `current_stop_price`.
- Money is `NUMERIC(18,2)`, prices `NUMERIC(20,10)` — never floating point.
- PostgreSQL check constraints reject impossible data (negative quantities, a long stop above entry, …).

### Futures reference data

Seeded from `backend/app/seed.py`, checked against CME Group contract-spec pages on 2026-10-11:

| Symbol | Quoted in | Tick | $ / point | $ / tick |
|---|---|---|---|---|
| ES / MES | index points | 0.25 | 50 / 5 | 12.50 / 1.25 |
| NQ / MNQ | index points | 0.25 | 20 / 2 | 5.00 / 0.50 |
| CL / MCL | USD per barrel | 0.01 | 1,000 / 100 | 10.00 / 1.00 |
| GC | USD per troy oz | 0.10 | 100 | 10.00 |
| ZN | points & ½ 32nds | 1/64 = 0.015625 | 1,000 | 15.625 |
| ZB | points & 32nds | 1/32 = 0.03125 | 1,000 | 31.25 |
| 6E | USD per EUR | 0.00005 | 125,000 | 6.25 |
| ZC | US cents per bushel | 0.25¢ | 50 per cent | 12.50 |

Specs can change; each row stores its `spec_source_url` and `spec_verified_on` date.

## Calculations

Defined once in `backend/app/domain/calculations.py` and returned by the API as `trade.metrics`.
`m` = point value (USD per 1.0 price move), `s` = +1 long / −1 short.

| Metric | Formula |
|---|---|
| Planned reward-to-risk (per target) | \|target − planned entry\| ÷ \|planned entry − initial stop\| |
| Initial dollar risk | \|avg entry − initial stop\| × entered qty × m (fees excluded) |
| Gross realized P&L | s × (avg exit − avg entry) × exited qty × m |
| Net realized P&L | gross − exit fees − entry fees × (exited ÷ entered) |
| Realized R | net realized P&L ÷ initial dollar risk |
| Unrealized P&L | only with a sourced, timestamped market price (none integrated yet) |

Money is rounded to cents half-up at the end; R and R:R to 2 decimals. Missing inputs give
"unavailable" with a reason — never 0.

## API (so far)

Interactive docs: http://127.0.0.1:8000/docs

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Backend + database status |
| GET / POST | `/api/portfolios` | List / create your portfolios |
| GET / PATCH / DELETE | `/api/portfolios/{id}` | Read / edit / delete (deletes its trades) |
| GET / POST | `/api/strategies` | List / create your strategies |
| GET | `/api/instruments?asset_class=&q=` | Futures (verified specs) and stocks |
| POST | `/api/instruments/stocks` | Add a stock symbol |
| GET / POST | `/api/instruments/{id}/contracts` | Futures contract months (e.g. ESZ2026) |
| GET | `/api/trades?portfolio_id=&status=&direction=&asset_class=&instrument_id=&strategy_id=&q=&date_from=&date_to=` | Search and filter your trades |
| POST | `/api/trades` | Create a trade (optional one entry + one exit) |
| GET / PUT / DELETE | `/api/trades/{id}` | Read / replace / delete |

Conventions: decimals are JSON **strings** (`"5000.25"`); timestamps must include a timezone and are
returned in UTC; validation errors are `422 {"detail": "Validation failed", "errors": [{"field", "message"}]}`;
another user's data returns `404`. Until Phase 6 every request runs as the local dev user.

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
cd frontend && npm test && npm run build && npm run lint
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
4. ✅ Journal for a local development user (data model, API, screens)
5. ✅ Risk and P&L calculations (tested)
6. Secure accounts and ownership
7. Strategies, filtering, analytics
8. CSV and PDF class reports
9. Scoped, revocable share links
10. Verified free economic data sources
11. More market data + market context on trades
12. Deployment instructions
