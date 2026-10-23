# Recruiter scoping is enforced by forced Row-Level Security on a non-owner role

Recruiters must only ever see Candidates in their assigned Regions, enforced in the data layer so that no future endpoint can bypass it. We enable and FORCE PostgreSQL RLS on `candidates`, with a policy that reads the Recruiter's Regions from the `recruiters` table using a transaction-scoped `app.recruiter_id` setting (`set_config(..., true)`). The API reads through a non-owner role without `BYPASSRLS`. With no context set, the policy returns zero rows (fail closed).

## Considered Options

- **Scoped query layer** (a single repository function that always adds `WHERE region = ANY(:regions)`): acceptable to the brief and simpler, but any query that skips the function leaks data. We still route reads through one repository function. RLS is the guarantee underneath it.

## Consequences

- Two database roles: an owner role for migrations and the import, and `techforce_app` for reads. The import uses an explicitly named owner connection because dedup must see every Candidate, so any code that bypasses RLS is easy to spot in review.
- The recruiter context must be set inside the same transaction as the query. Session-level `SET` would leak across pooled connections.
- Tests must run against real Postgres. The headline test runs a raw `SELECT * FROM candidates` as `techforce_app` with a Recruiter's context set.
