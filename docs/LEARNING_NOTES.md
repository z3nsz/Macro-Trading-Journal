# Learning Notes

Short explanations of concepts as they come up in the project.

## Milestone 1 — Architecture

- **Frontend**: the part that runs in the browser (React). Shows data and collects input.
- **Backend**: a program on a server (FastAPI). Enforces rules, does calculations, talks to the database.
- **Database**: permanent storage (PostgreSQL), organised as linked tables.
- **API**: the set of requests the backend agrees to answer — like a menu.
- **Endpoint**: one item on that menu: an HTTP method + URL, e.g. `GET /api/health`.
- **JSON**: the text format used to send data between frontend and backend (looks like a Python dict).
- **Component**: a reusable piece of UI written as a function that returns markup (e.g. `<BackendStatus />`).
- **Migration**: a versioned script that changes the database structure (Milestone 3).
- Calculations live in their own module (`domain/`), not in routes or UI, so they can be tested alone.
- Money uses `Decimal` / `NUMERIC`, never floats: `0.1 + 0.2 == 0.30000000000000004` in float math.

## Milestone 2a — First request

- **HTTP methods**: `GET` reads, `POST` creates, `PUT/PATCH` updates, `DELETE` removes.
- **Status codes**: `200` OK, `404` not found, `422` invalid input, `500` server error.
- **Virtual environment (`.venv`)**: a private copy of Python packages for this project only.
  `requirements.txt` lists exact versions so anyone can reproduce it.
- **`node_modules` / `package.json`**: the JavaScript equivalent.
- **Pydantic model** (`HealthResponse`): declares the exact shape of data; FastAPI validates and documents it.
- **Router**: a group of related endpoints, plugged into the app with a URL prefix (`/api`).
- **Port**: a numbered "door" on a computer. Backend uses 8000, Vite uses 5173.
- **Proxy**: Vite forwards any `/api/...` request from the browser to port 8000.
  The browser thinks it is talking to one site.
- **CORS** (Cross-Origin Resource Sharing): a browser rule that blocks a page from one origin
  (e.g. `localhost:5173`) reading responses from another (`localhost:8000`) unless the server allows it.
  The proxy avoids the issue in development; we'll configure it properly for deployment.
- **State**: data a component remembers between renders (e.g. "is the request still loading?").
- **TanStack Query `useQuery`**: fetches data and gives us `isPending` / `isError` / `data`
  so each screen can show loading, error and success states.
- **TypeScript interface** (`HealthResponse` in `health.ts`): mirrors the backend's Pydantic model,
  so a typo like `data.sever_time` is caught at build time.
- **Environment variables / `.env`**: configuration and secrets kept outside the code.
  `.env` is git-ignored; `.env.example` shows which variables exist, with placeholders.

## Milestone 3 — PostgreSQL & migrations

- **Database server**: PostgreSQL is its own program (port 5432). The backend connects to it like a client.
  `brew services start/stop postgresql@18` controls it.
- **Role**: a database login. We use a dedicated `macro_journal` role instead of an admin account,
  so the app only has the permissions it needs.
- **Table / row / column**: like a spreadsheet tab, its rows, and its typed headers.
- **Primary key**: a unique ID for each row (`users.id`). **Unique index**: the database itself
  refuses two users with the same email — a rule enforced even if app code has a bug.
- **`timestamp with time zone`**: we always store moments in time with a timezone (UTC inside Postgres).
  Essential for trade timestamps across markets.
- **ORM (SQLAlchemy)**: lets us write `User(email=...)` in Python instead of raw SQL.
  A **model** is a Python class that describes one table.
- **Session**: one unit of work with the database. `flush` sends changes; `commit` makes them permanent;
  `rollback` throws them away.
- **Dependency injection (`Depends(get_db)`)**: FastAPI creates a session for each request, passes it
  into the endpoint, and closes it afterwards — endpoints never manage connections themselves.
- **Connection pool**: the backend keeps a few database connections open and reuses them (faster).
  Side effect we saw: PostgreSQL's normal ("smart") shutdown waits for those idle connections;
  `pg_ctl stop -m fast` disconnects them. `pool_pre_ping=True` lets the app recover automatically
  when the database comes back.
- **Migration**: a versioned script with `upgrade()` and `downgrade()`.
  Alembic stores the current version in a table called `alembic_version`.
  Workflow: edit a model → `alembic revision --autogenerate -m "..."` → **read the generated file** →
  `alembic upgrade head`. Autogenerate is a draft, not gospel — always review it.
- **Test database**: tests use `macro_journal_test`, rebuilt from migrations on each run.
  Each test runs inside a transaction that is rolled back, so tests never affect each other or real data.
- **Graceful degradation**: if the database is down, `/api/health` still answers (`"degraded"`) instead
  of crashing. The same principle will keep the journal working when market-data providers fail.

## Milestone 4a — Journal data model

- **Normalization**: store each fact once. ES's $50/point lives in one `instruments` row, not copied into
  every trade, so a single verified value feeds every calculation.
- **Foreign key**: a column pointing to another table's row (`trades.portfolio_id → portfolios.id`).
  `ondelete` decides what happens when the parent is deleted:
  - `CASCADE` — delete children too (delete a portfolio → its trades and executions go).
  - `RESTRICT` — refuse (can't delete ES while trades use it).
  - `SET NULL` — keep the child, clear the link (delete a strategy → trades keep existing, unassigned).
- **One-to-many**: one trade has many executions. Drawn as `trades ──< executions`.
- **Check constraint**: a rule PostgreSQL enforces on every row (e.g. `quantity > 0`, a long's stop below entry).
  We use strings + check constraints instead of PostgreSQL ENUM types because they are easier to extend later.
- **Trade vs. execution**: the trade is the plan and reasoning; executions are actual fills.
  Partial exit = several exit executions. Average entry, realized P&L, etc. are *calculated* from executions.
- **Initial vs. current stop**: R-multiples measure results against the risk you planned when you entered,
  so the initial stop is never overwritten.
- **Quoted price units differ by contract**: ES in index points, CL in $/barrel, ZN in points and 32nds,
  ZC in *cents* per bushel. `point_value` converts a 1.0 move in the quote into dollars per contract:
  `dollar P&L = price change × point_value × quantity`. Tick value = `tick_size × point_value`.
- **Seed data**: reference data loaded by a script. Idempotent = running it twice gives the same result.
- **Testing the tests**: we temporarily broke NQ's multiplier and confirmed a test failed. A test that can't
  fail proves nothing.

## Milestone 4b — Journal API

- **Layers** (each only talks to the one below):
  `api/` (HTTP in/out) → `services/` (ownership, database) → `domain/` (pure rules) ; `schemas/` = data shapes.
  Pure rules are trivially testable: 26 rule tests run in 0.02 s with no database.
- **CRUD ↔ HTTP**: Create = `POST`, Read = `GET`, Update = `PUT` (replace all) / `PATCH` (change some),
  Delete = `DELETE`.
- **Status codes**: 201 Created, 204 No Content, 404 Not Found, 409 Conflict, 422 Unprocessable (invalid data),
  503 Service Unavailable.
- **Query parameters**: the `?status=open&q=cpi` part of a URL — used for filtering and search.
- **Path parameters**: the `{trade_id}` in `/api/trades/{trade_id}`.
- **Ownership checks**: every query includes `WHERE portfolio.user_id = current_user`. Someone else's trade
  gives 404 (not 403), so outsiders can't even learn it exists.
- **Dependency override**: `get_current_user` is a single function every endpoint depends on. Today it
  returns the dev user; tests swap it to act as Alice or Bob; Phase 6 swaps in real login.
- **Derived data**: status is calculated from fills, never typed by hand, so it can't contradict them.
- **Decimals in JSON as strings**: JSON numbers are floats in JavaScript; `"5000.25"` keeps it exact.
- **UTC everywhere**: the database stores instants; the server returns them in UTC (`Z`);
  the UI will convert to the viewer's local time for display.
- **Bugs met**: (1) Pydantic checks a `pattern` before `to_upper`, so `aapl` was rejected → allow lowercase
  in the pattern. (2) Replacing a trade's targets could insert the new TP1 before deleting the old TP1,
  breaking the unique rule → delete old rows first, then insert.

## Milestone 4c — Journal screens

- **Routing**: React Router maps URLs to pages (`/trades/:tradeId` → `TradeDetailPage`). `:tradeId` is read
  with `useParams()`. `<Layout>` holds the header; `<Outlet />` is where the current page appears.
- **Filters in the URL** (`useSearchParams`): `/trades?status=open&q=cpi` can be bookmarked and survives
  the back button.
- **Controlled form**: input `value` comes from state; `onChange` updates state. We keep everything as
  strings exactly as typed and convert once on submit (`toInput`).
- **Mutation + invalidation**: after saving, `invalidateQueries(['trades'])` marks the cached list stale so it
  reloads — the list never shows outdated data.
- **Two layers of validation**: the browser's `required` stops obviously incomplete forms instantly; the
  server's rules are the real authority and their messages are shown next to the matching field.
- **Responsive design**: Tailwind's `md:` prefix applies a style from 768 px up. The journal shows a table on
  desktop (`hidden md:block`) and cards on phones (`md:hidden`).
- **Debouncing**: the search box waits 300 ms after you stop typing before querying the server.
- **Deriving instead of syncing**: rather than an effect that copies "first portfolio" into state, we
  compute `form.portfolio_id || firstPortfolio` during render — simpler and avoids an extra render.
- **Money formatting**: fees display as `$4.20` with string-based formatting, never `$4.2`.

## Milestone 5 — Risk & P&L calculations

**Worked example** — ES long 2 contracts, m = $50. Plan: entry 5000, stop 4980, TP1 5040, TP2 5060.

| Step | Calculation | Result |
|---|---|---|
| Planned R:R TP1 / TP2 | 40 ÷ 20, 60 ÷ 20 | 2.00 / 3.00 |
| Initial risk (filled 5000.25) | 20.25 × 2 × $50 | $2,025.00 |
| Gross (exit 2 @ 5040.50) | 40.25 × 2 × $50 | $4,025.00 |
| Net (fees 4.20 + 4.20) | 4,025.00 − 8.40 | $4,016.60 |
| Realized R | 4,016.60 ÷ 2,025.00 | 1.98R |
| Partial: exit 1 @ 5040 | 1,987.50 − (4.20 + 2.10) | $1,981.20 = 0.98R so far |

- **Planned vs. realized**: planned R:R comes from the plan (2.00 at TP1); realized R from what happened
  (1.98, lower because of slippage and fees). Keeping both lets you see execution quality.
- **R-multiple**: results measured in units of the risk you took. +2R means you made twice what you risked.
  It makes a $50 trade in MES comparable with a $5,000 trade in ES.
- **Weighted average**: 1 contract @ 5000 + 3 @ 5004 = average 5003 (each fill weighted by its quantity).
- **Fee allocation on partial exits**: only the closed share of entry fees is counted now; the rest is
  counted when the remaining position closes.
- **Rounding**: calculate at full precision, round money once at the end (half-up: 515.625 → 515.63).
  Rounding in the middle accumulates errors.
- **Unavailable ≠ zero**: a trade without a stop has no defined R. Showing 0R would be a lie that also
  distorts averages later, so we return null plus a reason.
- **Single source of truth**: the frontend never re-calculates; it displays the backend's numbers.
