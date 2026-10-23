# 07: README, NOTES.md and clean-machine run

**What to build:** A reviewer can go from a clean clone to a working stack and a passing test suite using only the README, and can read every rule and judgement call in NOTES.md.

**Blocked by:** 04: Merge, ID Collision and idempotent re-import; 05: Search, status filter and pagination; 06: Recruiter view end-to-end smoke

**Status:** ready-for-agent

- [ ] README: a clean-machine quick start (`docker compose up` → open the UI → a one-line `curl` import), local development (`uv`, npm), and running the tests, including the `e2e` marker.
- [ ] NOTES.md (half a page to a page) covers:
  - The merge and conflict rules and every normalization rule.
  - The documented simplifications: open import endpoint, US date order, no salary currency, unvalidated phone.
  - The AI usage log: what was delegated, what wasn't, and at least one concrete correction.
  - What I'd do next: E.164 phones, `unaccent` search, an Admin-only import, statuses beyond four.
- [ ] Verified from scratch: `docker compose down -v`, then `docker compose up`, then an import, then flipping Caleb ↔ Marisol in the UI.
- [ ] The full pytest suite (unit, integration, RLS and e2e) passes on camera.
