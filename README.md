# TechForce Candidate Import & Recruiter View

Imports the legacy `candidates_import.csv` into PostgreSQL with documented
normalization and Merge rules, and shows each Recruiter only the Candidates in
their Regions. Scope is enforced by PostgreSQL Row-Level Security.

- **Backend:** FastAPI (async), SQLAlchemy 2.0 Core on asyncpg, Alembic, uv. Python 3.12.
- **Frontend:** Vite, React, TypeScript and TanStack Query.
- **Database:** Postgres 16.

The rules and judgement calls are in [NOTES.md](NOTES.md), the vocabulary is in
[GLOSSARY.md](GLOSSARY.md), and the decisions are in [docs/adr/](docs/adr/).

## Quick start (clean machine, Docker only)

```sh
docker compose up
```

This builds the images on the first run (add `--build` after pulling changes)
and starts three services. The API runs the migrations on start: schema,
roles, RLS policies and the Recruiter roster.

| Service | URL |
| --- | --- |
| UI | http://localhost:5173 |
| API | http://localhost:8000 (e.g. `/api/v1/recruiters`) |
| Postgres | `localhost:5433` |

The database starts empty. Import the CSV as the Admin (Dana, `R-101`). The import is Admin-only:

```sh
curl -X POST http://localhost:8000/api/v1/candidates/import \
  -H "X-Recruiter-Id: R-101" -F file=@candidates_import.csv
```

The Import Report shows `"imported": 40`, `"merged": 3` and 10 `rejected` rows,
each with a reason. Re-running the import is harmless: it reports 0 imported and
43 merged.

Then open http://localhost:5173 and use **Viewing as** to flip between Caleb
Nguyen (US-MW, US-NE: 18 Candidates) and Marisol Vega (PH-MNL, CO-BOG: 9 Candidates).

You can also read the list directly:

```sh
curl -H "X-Recruiter-Id: R-102" "http://localhost:8000/api/v1/candidates?search=raman&status=interviewing"
```

**Why port 5433?** Compose publishes Postgres on host port **5433** (container
5432), so it doesn't clash with a local Postgres already on 5432. Every port is
bound to `127.0.0.1` only. To change any default, copy `.env.example` to `.env`
(for example, `POSTGRES_HOST_PORT`).

To reset everything, run `docker compose down -v`. This deletes the database volume.

## Local development

You need uv, Node 20+ and Docker (for Postgres).

```sh
docker compose up -d db              # Postgres only, on localhost:5433

# API on :8000. Settings default to localhost:5433; a repo-root .env overrides them.
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn --factory app.main:create_app --reload

# UI on :5173. In another shell; Vite proxies /api to localhost:8000.
cd frontend
npm install
npm run dev
```

Note that the compose `web` image copies the source rather than mounting it.
After a UI change, rebuild it with `docker compose up -d --build web`, or use
`npm run dev` as shown above.

## Tests

**The default suite** covers the unit (domain rules), API integration and RLS
tests. It needs only the compose Postgres:

```sh
docker compose up -d db
cd backend && uv run pytest
```

The suite uses its own database, `techforce_test` (override it with
`TEST_DATABASE_NAME`). The suite creates it if it's missing, migrates it once
per session, and truncates `candidates` between tests. Your dev data is never
touched.

**The e2e suite** (marker `e2e`) is deselected by default. It runs Playwright
against the full running stack. It imports the CSV through the API itself, and
re-importing is idempotent.

```sh
docker compose up -d --build
cd backend
uv run playwright install chromium   # once
uv run pytest -m e2e
```

Each test reads the expected scoped total for its Recruiter from the API and
checks the UI shows the same, so extra imports into the stack's database don't
break it. If the stack isn't reachable, the e2e tests are skipped with a
reason.
