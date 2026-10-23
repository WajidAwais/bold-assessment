# 01: Walking skeleton: clean rows from CSV to table

**What to build:** A reviewer runs `docker compose up` on a clean machine, uploads `candidates_import.csv` to the import endpoint, and sees the well-formed Candidates in the React table, Unicode names intact. This is the thinnest end-to-end path through compose, migrations, the layered backend (api / services / domain / repositories / db), the Import Report and the UI. Validation, Merge and Scope come in later tickets: here, rows that don't fit the schema may simply be reported as Rejections with a generic reason. See the spec at `.scratch/candidate-import/spec.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Monorepo with backend and frontend. Compose runs Postgres 16, the API (runs `alembic upgrade head` on start, then serves) and the Vite dev server (proxies `/api`). A `.env.example` holds the dev defaults.
- [ ] An Alembic migration creates `candidates` (surrogate key, unique email, unique Legacy ID, canonical Region and status constraints) and `recruiters`, and seeds the 5 Recruiters from the roster.
- [ ] `POST /api/v1/candidates/import` (multipart `file`) inserts Candidates in batches inside a single transaction (no row-at-a-time writes) using SQLAlchemy Core, and returns an Import Report `{imported, merged, rejected, merges}`.
- [ ] `GET /api/v1/recruiters` returns id, full name, role and Regions.
- [ ] `GET /api/v1/candidates` returns `{items, total, page, page_size}` with the agreed item fields (no salary, phone or notes). It is temporarily unscoped; Scope arrives in ticket 02.
- [ ] The React table shows name, email, region, role, status and applied date. `Nguyễn Thị Hoa` renders correctly.
- [ ] Test harness: a separate test database on the compose Postgres, migrations run once per session, `candidates` truncated per test, `pytest-asyncio` + `httpx.AsyncClient`. One passing test imports rows and lists them.
