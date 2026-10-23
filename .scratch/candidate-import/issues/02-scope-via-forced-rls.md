# 02: Scope enforced by forced RLS, plus Recruiter switcher

**What to build:** A Recruiter identified by `X-Recruiter-Id` sees only Candidates in their Scope, and an Admin sees all. The database enforces this through forced Row-Level Security, so no endpoint or raw query can bypass it. In the UI, a reviewer flips between Caleb and Marisol and watches the data change, with no stale rows. See ADR-0002.

**Blocked by:** 01: Walking skeleton

**Status:** ready-for-agent

- [ ] A migration creates the non-owner `techforce_app` role (no `BYPASSRLS`) with read grants, and enables **and forces** RLS on `candidates`. The policy admits a row when the Recruiter in the transaction-local `app.recruiter_id` setting is an Admin or has the row's Region assigned. No setting means no rows.
- [ ] Reads go through a scoped connection: open a transaction, `set_config('app.recruiter_id', id, true)`, then query. The import keeps using an explicitly named owner connection.
- [ ] `X-Recruiter-Id` missing → 401; unknown → 403 (not an empty 200).
- [ ] The UI Recruiter switcher is populated from `GET /api/v1/recruiters` and labels each Recruiter with their Regions. Every candidates query key includes the Recruiter ID. A 403 shows as an error, not an empty table.
- [ ] Test: Caleb cannot retrieve a PH-MNL Candidate; Dana (Admin) can.
- [ ] Test: unknown ID → 403; missing header → 401.
- [ ] Test: as `techforce_app` with Caleb's context, a raw `SELECT * FROM candidates` returns only US-MW and US-NE rows. With no context set, it returns zero rows.
