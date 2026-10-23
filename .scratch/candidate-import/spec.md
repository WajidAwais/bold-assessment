# Spec: Candidate Import & Scoped Recruiter View

Status: ready-for-agent

## Problem Statement

TechForce recruiters work from a legacy candidate export that is unusable as-is. It has duplicate people, one Legacy ID shared by two different people, malformed emails, inconsistent Region codes, statuses and dates, salaries written as free text, and rows crafted to attack the database. Recruiters also need to see only the Candidates in their own Regions. Today nothing stops one Recruiter from seeing another's Candidates, and nothing tells the people running the import what was loaded, what was merged or why a row was refused.

## Solution

An import endpoint that takes the raw CSV and turns it into clean Candidates in PostgreSQL. It applies explicit, documented normalization and merge rules and never drops a row silently: every row ends up imported, merged, or rejected with a reason in the Import Report. Importing the same file again changes nothing.

A read API returns Candidates within the caller's Scope. Scope is enforced by PostgreSQL Row-Level Security, so no endpoint, present or future, can return a Candidate outside it.

A single-page Recruiter view shows the scoped table with search, a status filter, and a Recruiter switcher. Flipping between Caleb and Marisol visibly changes the data.

## User Stories

### Import

1. As an Admin, I want to upload the legacy CSV to one endpoint, so that the whole file loads in a single action.
2. As an Admin, I want an Import Report with counts of imported and merged rows, so that I can confirm the outcome at a glance.
3. As an Admin, I want every Rejection listed with its row number, Legacy ID and reason, so that I can fix the source data.
4. As an Admin, I want all of a row's problems in its reason, so that I don't fix one problem only to discover the next on re-import.
5. As an Admin, I want row numbers to count CSV records rather than physical lines, so that a multi-line note doesn't shift every number after it.
6. As an Admin, I want each Merge listed with the Legacy ID it was merged into, so that no Legacy ID disappears silently.
7. As an Admin, I want re-importing the same file to create nothing new, so that an accidental double upload is harmless.
8. As an Admin, I want an import to succeed or fail as a whole, so that a crash never leaves the database half-loaded.
9. As an Admin, I want a file with missing columns refused before any row is processed, so that a wrong file can't partially load.
10. As an Admin, I want a file that isn't valid UTF-8 refused, so that Unicode names are never silently mangled.
11. As an Admin, I want a file exported from Excel with a byte-order mark accepted, so that a common export quirk doesn't block me.
12. As an Admin, I want oversized files (over 5 MB) refused, so that the service isn't overwhelmed.

### Candidate identity and Merge

13. As a Recruiter, I want one Candidate per person, identified by their normalized email, so that I never contact the same person twice.
14. As an Admin, I want an exact duplicate row to Merge into the existing Candidate, so that repeated exports don't create duplicates.
15. As an Admin, I want a row with the same email but a different Legacy ID to Merge into the first-seen Candidate, so that re-applications are recognized.
16. As an Admin, I want the first-seen Candidate's values to win and later rows to fill only blanks, so that a degraded later record (e.g. name "A.") never overwrites better data.
17. As an Admin, I want Candidates already in the database treated as first-seen, so that the merge rule is the same within a file and across imports.
18. As an Admin, I want a row whose Legacy ID already belongs to a Candidate with a different email rejected as an ID Collision, so that one person is never overwritten by another.
19. As an Admin, I want a row whose email matches one Candidate but whose Legacy ID belongs to another to Merge by email, so that identity is always decided by email.

### Validation and normalization

20. As an Admin, I want emails trimmed and lowercased, so that `  Alicia.Trent@Gmail.com ` and `alicia.trent@gmail.com` are recognized as the same Candidate.
21. As an Admin, I want malformed emails (`[at]`, no `@`) rejected rather than repaired, so that we never guess someone's contact address.
22. As an Admin, I want rows without an email rejected, so that every Candidate has an identity.
23. As an Admin, I want Region codes matched ignoring case, whitespace and separators (`us-mw`, ` CO-BOG `, `USW`), so that trivially different spellings aren't lost.
24. As an Admin, I want unknown or missing Regions rejected, so that no Candidate exists outside every Recruiter's Scope.
25. As an Admin, I want statuses matched case-insensitively against `active`, `screening`, `interviewing` and `withdrawn`, so that `ACTIVE` is accepted.
26. As an Admin, I want misspelled or unknown statuses (`actve`, `on hold`) rejected, so that we never guess a Candidate's pipeline state.
27. As an Admin, I want dates accepted as `YYYY-MM-DD`, `MM/DD/YYYY` or `DD-Mon-YYYY`, so that common legacy formats load.
28. As an Admin, I want impossible dates (`2026-02-30`) rejected, so that corrupt data is surfaced rather than hidden.
29. As an Admin, I want a missing applied date allowed, so that an otherwise valid Candidate isn't lost over an optional field.
30. As an Admin, I want salaries like `$95,000`, `97,500` and `85k` stored as whole numbers, so that they can be compared.
31. As an Admin, I want salaries that aren't numbers (`negotiable`) stored as null without rejecting the row, so that a valid Candidate isn't lost over a soft field.
32. As a Recruiter, I want names with any script and diacritics (`Nguyễn Thị Hoa`, `Tomás`, `Jürgen`) accepted and NFC-normalized, so that people's names are respected.
33. As an Admin, I want names containing non-name characters (e.g. `);`) rejected, so that garbage never reaches recruiter-facing data.
34. As an Admin, I want free-text notes stored exactly as written, including quotes and multiple lines, so that recruiter context is preserved.
35. As an Admin, I want phone numbers stored trimmed and otherwise as given, so that no contact detail is lost to over-eager parsing.

### Security

36. As a security reviewer, I want SQL-looking content in any field to be stored and returned as inert text, so that SQL injection is impossible.
37. As a security reviewer, I want `%` and `_` in search terms treated literally, so that search can't be widened by wildcard characters.
38. As a security reviewer, I want writes batched rather than inserted row by row, so that imports are efficient and atomic.

### Scoped read API

39. As a Recruiter, I want to identify myself with an `X-Recruiter-Id` header, so that I get my Scope without a login flow.
40. As a Recruiter, I want to see only Candidates in my assigned Regions, so that I work only my own pipeline.
41. As an Admin, I want to see every Candidate, so that I can oversee all Regions.
42. As a security reviewer, I want an unknown Recruiter ID to get 403, so that a bad identity isn't mistaken for an empty Scope.
43. As a security reviewer, I want a missing `X-Recruiter-Id` to get 401, so that "no identity" is distinguished from "wrong identity".
44. As a security reviewer, I want Scope enforced by the database, so that a new endpoint or raw query can't leak Candidates outside the Recruiter's Scope.
45. As a security reviewer, I want a query with no Recruiter context to return zero Candidates, so that the system fails closed.
46. As a Recruiter, I want to search by name, email or desired role, case-insensitively, so that I can find a Candidate quickly.
47. As a Recruiter, I want to filter by status, so that I can focus on one pipeline stage.
48. As a Recruiter, I want an invalid status filter to return a clear validation error, so that typos don't silently return nothing.
49. As a Recruiter, I want results paginated with a total count of my Scope, so that I can page through large result sets.
50. As a Recruiter, I want a stable sort (newest applied first, blank dates last), so that pages never overlap or skip Candidates.
51. As a security reviewer, I want the list to leave out salary, phone and notes, so that personal data isn't exposed when the table doesn't need it.
52. As the Recruiter view, I want a list of Recruiters with their names and Regions, so that the switcher can be populated without duplicating the roster.

### Recruiter view

53. As a Recruiter, I want a table showing name, email, region, role, status and applied date, so that I can scan my pipeline.
54. As a Recruiter, I want a search box that updates results as I type (debounced), so that searching feels responsive without flooding the API.
55. As a Recruiter, I want a status filter offering exactly the four statuses, so that I can only pick valid values.
56. As a reviewer, I want a Recruiter switcher listing all five Recruiters with their Regions, so that I can flip between Caleb and Marisol and watch the data change.
57. As a reviewer, I want switching Recruiters to never show the previous Recruiter's cached rows, so that the view can't leak data across Scopes.
58. As a Recruiter, I want the page to reset to 1 when I change Recruiter, search or status, so that I'm never on an empty page.
59. As a Recruiter, I want Unicode names to display correctly, so that `Nguyễn Thị Hoa` isn't mangled.
60. As a Recruiter, I want visible loading, empty and error states, so that I always know what the view is doing.
61. As a reviewer, I want a 403 for an unknown Recruiter shown as an error rather than an empty table, so that authorization failures are obvious.

### Setup and delivery

62. As a reviewer, I want one `docker compose up` to start the database, API and UI on a clean machine, so that I can evaluate without installing toolchains.
63. As a reviewer, I want the schema, roles, RLS policies and Recruiter roster created by migrations, so that setup is repeatable.
64. As a developer, I want to run the API and tests locally against the compose database, so that the feedback loop is fast.
65. As a reviewer, I want a README with quick start, local development and test instructions, so that every path is documented.
66. As a reviewer, I want NOTES.md recording the merge and normalization rules, the AI usage log and next steps, so that the decisions are explicit.

## Implementation Decisions

### Architecture

- Monorepo with a backend and a frontend. Docker Compose runs three services: Postgres 16, the API (runs migrations on start, then serves), and the Vite dev server (proxies `/api` to the API).
- The backend is async FastAPI with SQLAlchemy 2.0 **Core** (not the ORM) on asyncpg, Alembic for migrations, and `uv` for Python tooling.
- The backend is split into layers, with dependencies pointing only downward:
  - **api**: routers, dependencies, request/response models and status codes. Nothing else.
  - **services**: use-case orchestration. An import service (parse → validate → merge → batched persist → report) and a candidate service (the single seam for scoped reads). No SQL, no HTTP.
  - **domain**: pure Python with no I/O. The Candidate Pydantic v2 model, the Status and Region enums, normalization rules, and first-seen Merge and ID Collision detection.
  - **repositories**: SQLAlchemy Core only. The only place SQL lives. One repository for candidates, one for recruiters.
  - **db**: engine, table metadata, a *scoped connection* that opens a transaction and sets the Recruiter context, and an explicitly named *owner connection* used only by the import.
- No generic base repository or interface classes; there is one implementation of each.

### Candidate identity and Merge (ADR-0001)

- A Candidate's identity is its normalized email. The Legacy ID is stored, unique, and secondary.
- First-seen wins. Later rows with the same email fill only null fields. The database counts as first-seen, so re-imports are idempotent.
- An ID Collision (a row that would create a new Candidate with a Legacy ID owned by a different email) is rejected. When a row's email matches an existing Candidate, the email wins and the row Merges, whatever its Legacy ID.
- Each import runs in a single transaction. Existing emails and Legacy IDs are looked up in bulk; inserts and blank-fills are batched, with no row-at-a-time writes in a loop.

### Validation rules

- **Required:** email, first name, last name, Region, status. **Nullable:** phone, desired role, salary, applied date, source, notes.
- **Email:** trim, lowercase the whole address, validate with Pydantic `EmailStr` (offline, no deliverability check). Never repaired. No provider-specific aliasing.
- **Region:** trim, uppercase, strip hyphens, spaces and underscores, then match exactly against the six canonical codes stripped the same way. No fuzzy or alias matching.
- **Status:** a four-value enum (`active`, `screening`, `interviewing`, `withdrawn`), matched case-insensitively after trimming. No typo correction.
- **Applied date:** one of `YYYY-MM-DD`, `MM/DD/YYYY` (US order only) or `DD-Mon-YYYY` (English month, case-insensitive). Empty → null. Impossible dates → rejected. No future-date check.
- **Salary:** strip `$`, `,` and whitespace, accept an optional `k`/`K` suffix (×1000), and require a positive integer. Anything else → null, and the row is still imported. No currency is stored.
- **Names:** NFC-normalized, 1–100 characters, allow-list of Unicode letters, combining marks, space, apostrophe, hyphen and period.
- **Phone, desired role, source, notes:** trimmed, otherwise stored verbatim. Phone is not validated.

### Import API contract

- `POST /api/v1/candidates/import`, `multipart/form-data` with a single `file` field. **Admin-only**: `X-Recruiter-Id` missing → 401, unknown or non-Admin → 403. (Changed from "open" during implementation: because a Merge fills blanks on existing Candidates, an open import would let anyone write into anyone's record.)
- Decoded as UTF-8 with a BOM tolerated. Invalid UTF-8 → 400. Missing expected columns → 400 naming them (extra columns ignored). Over 5 MB → 413.
- Response, the Import Report:
  - `imported`: count of new Candidates.
  - `merged`: count of rows Merged.
  - `rejected`: a list of `{row, candidate_id, reason}`.
  - `merges`: a list of `{row, candidate_id, merged_into}`.
- `row` is the 1-based CSV record number, header excluded. A `reason` joins every validation error with `; `, using fixed prefixes: `missing <field>`, `invalid email`, `unknown region`, `unknown status`, `invalid date`, `invalid characters in <field>`, `candidate_id collision`.

### Read API contract

- `GET /api/v1/candidates?search=&status=&page=&page_size=`:
  - Search is a case-insensitive substring match on first name, last name, full name, email and desired role. LIKE wildcards are escaped. Accent-sensitive.
  - `status` is optional; an invalid value → 422.
  - `page` defaults to 1. `page_size` defaults to 25, maximum 100.
  - Ordered by applied date descending (nulls last), then id.
  - Response `{items, total, page, page_size}`, where `total` is the scoped count.
  - Each item has id, legacy ID, first name, last name, email, Region, desired role, status and applied date. No salary, phone or notes.
- `X-Recruiter-Id`: missing → 401; unknown → 403.
- `GET /api/v1/recruiters` returns id, full name, role and Regions. No header required.

### Scoping via Row-Level Security (ADR-0002)

- **Schema:**
  - `recruiters` table, seeded from the roster by migration.
  - `candidates` table with a surrogate primary key, a unique email, a unique Legacy ID, and Region and status constrained to the canonical values.
- **Roles:**
  - An owner role runs migrations and the import.
  - `techforce_app` (non-owner, no `BYPASSRLS`) serves reads.
- **Policy:**
  - RLS is enabled **and forced** on `candidates`.
  - The policy admits a row when the Recruiter identified by the transaction-local `app.recruiter_id` setting is an Admin or has the row's Region assigned.
  - With no setting, no rows are visible.
- **Per request:** resolve the Recruiter (401/403), open a transaction, `set_config('app.recruiter_id', id, true)`, then run the plain filtered query. The setting is transaction-local so it can't leak across pooled connections.

### Frontend

- Vite, React and TypeScript, with TanStack Query and plain `fetch`. Minimal CSS.
- The Recruiter switcher is fed by the recruiters endpoint and labels each Recruiter with their Regions.
- Every query key includes the Recruiter ID, search term, status and page.
- Search is debounced at about 300 ms. The page resets to 1 when the Recruiter, search or status changes.
- Loading, empty and error states are shown, and a 403 is displayed as an error.

## Testing Decisions

- **What makes a good test:** it exercises external behaviour through a seam: HTTP responses, rule outcomes, and rows visible to a database role. It never asserts on internal calls, private helpers or SQL text. Tests use the real `candidates_import.csv` rows wherever possible, so the fixtures are the client's actual data.
- **Seam 1, HTTP API (primary):** `httpx.AsyncClient` against the app and a real Postgres test database. It covers:
  - Import of the real CSV → exactly **40 imported / 3 merged / 10 rejected**, with the specific rejected rows and reasons and the specific merges.
  - Re-import → `imported: 0, merged: 43`, with the same 10 rejections.
  - Injection: C-1037's notes payload round-trips unchanged, the `candidates` table still exists with the correct count, and the C-1036 DROP payload is sent through notes and through `search=` without effect.
  - Literal `%` in search.
  - Upload errors: 400, 413.
  - Authorization: Caleb can't retrieve a PH-MNL Candidate, Dana (Admin) can, an unknown ID → 403, and a missing header → 401.
  - Status filter, pagination and the scoped total.
- **Seam 2, domain rules (pure, no I/O):** table-driven tests of every normalization rule and of first-seen Merge and ID Collision detection, built from real CSV rows. These give fast, precise failures per rule.
- **Seam 3, database role:** connect as `techforce_app`.
  - With Caleb's context set, a raw `SELECT * FROM candidates` returns only US-MW and US-NE.
  - With no context set, the same query returns zero rows (fails closed).
  - This proves Scope holds beneath every endpoint.
- **Seam 4, Recruiter view end-to-end:** a small Playwright smoke suite (pytest-playwright, so it runs in the same pytest session) against the running compose stack, marked `e2e` so it can be run separately. It checks:
  - Selecting Caleb shows only US-MW and US-NE rows.
  - Switching to Marisol shows only PH-MNL and CO-BOG rows, with none of Caleb's left behind.
  - `Nguyễn Thị Hoa` renders correctly.
  - Search and the status filter narrow the table.
  - The agent also checks the UI by hand in a browser during implementation.
- **Test database:** a separate test database on the compose Postgres. `alembic upgrade head` runs once per session (the same migration as production), and `candidates` is truncated between tests. Transaction-rollback isolation is not used, because the RLS tests need committed data seen through a different role.
- **Async:** `pytest-asyncio`.
- **Prior art:** none. This is a greenfield repo.
- The full suite runs on camera before the recording stops.

## Out of Scope

- Login and real authentication. Identity is the `X-Recruiter-Id` header only.
- Phone validation or E.164 normalization.
- Accent-insensitive search (`unaccent`).
- Currency handling for salary.
- Provider-specific email aliasing (Gmail dots, `+tags`).
- Typo correction or fuzzy matching for Region or status.
- Editing, deleting or creating Candidates outside the import.
- Statuses beyond the four observed values.
- Styling beyond the minimum.
- Production deployment and an nginx build of the frontend.

## Further Notes

- **Expected Import Report for the provided CSV:**
  - Imported (40): C-1001–C-1030, C-1037, C-1038, C-1039, C-1041, C-1042, C-1043, C-1044, C-1046, C-1049, C-1050.
  - Merged (3): row 31 C-1004 → C-1004, row 32 C-1031 → C-1001, row 33 C-1032 → C-1016.
  - Rejected (10): rows 34 C-1033, 35 C-1034, 36 C-1035, 37 C-1036, 41 C-1040, 46 C-1045, 48 C-1047, 49 C-1048, 52 C-1010 (collision), 53 C-1051.
- **Recording constraints:**
  - 3 hours of recorded time, with one commit per slice in the agreed plan: scaffold → db/RLS → domain rules → import endpoint → scoped list → recruiter view → docs → clean run.
  - Keep a live AI usage log from minute one.
  - Tests come before endpoints. If time runs short, the frontend polish is cut first, then the e2e smoke suite, never the API tests.
- **Vocabulary:** see `GLOSSARY.md`. Architectural decisions: `docs/adr/0001-candidate-identity-is-normalized-email.md` and `docs/adr/0002-recruiter-scoping-via-forced-rls.md`.
