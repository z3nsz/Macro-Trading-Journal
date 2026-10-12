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
