# 06: Recruiter view end-to-end smoke (Playwright)

**What to build:** An automated browser check that the Recruiter view behaves correctly against the running compose stack, so the front end is verified rather than only eyeballed. It runs under pytest via pytest-playwright and is marked `e2e`, so it can run in the same session or on its own.

**Blocked by:** 05: Search, status filter and pagination

**Status:** resolved

- [x] Selecting Caleb shows only US-MW and US-NE rows.
- [x] Switching to Marisol shows only PH-MNL and CO-BOG rows, and none of Caleb's rows remain visible.
- [x] `Nguyễn Thị Hoa` renders correctly in the table.
- [x] Typing a search term and choosing a status both narrow the table.
- [x] The suite is marked `e2e` and documented as needing the compose stack running.
- [x] The UI is also checked by hand in a browser during implementation.
