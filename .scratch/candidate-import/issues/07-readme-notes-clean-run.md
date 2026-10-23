# 07: README, NOTES.md and clean-machine run

**What to build:** A reviewer can go from a clean clone to a working stack and a passing test suite using only the README, and can read every rule and judgement call in NOTES.md.

**Blocked by:** 04: Merge, ID Collision and idempotent re-import; 05: Search, status filter and pagination; 06: Recruiter view end-to-end smoke

**Status:** ready-for-agent

- [x] README: a clean-machine quick start (`docker compose up` → open the UI → a one-line `curl` import sending the Admin header `X-Recruiter-Id: R-101`), local development (`uv`, npm), and running the tests, including the `e2e` marker.
- [x] NOTES.md (half a page to a page) covers:
  - The merge and conflict rules and every normalization rule.
  - The documented simplifications: US date order, no salary currency, unvalidated phone.
  - The AI usage log: what was delegated, what wasn't, and at least one concrete correction.
  - Why import is Admin-only: the blank-fill Merge hole found by security review, recorded as an AI-assisted catch.
  - What I'd do next: E.164 phones, `unaccent` search, real authentication, statuses beyond four.
- [x] Verified from scratch: `docker compose down -v`, then `docker compose up`, then an import, then flipping Caleb ↔ Marisol in the UI.
- [x] The full pytest suite (unit, integration, RLS and e2e) passes on camera.
