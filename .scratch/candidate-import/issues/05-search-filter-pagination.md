# 05: Search, status filter and pagination

**What to build:** A Recruiter narrows their scoped list with text search and a status filter and pages through it, both in the API and the UI. The total reflects only their Scope. Search terms, including SQL-looking text and LIKE wildcards, are matched as literal text.

**Blocked by:** 02: Scope enforced by forced RLS, plus Recruiter switcher

**Status:** ready-for-agent

- [x] `search` is a case-insensitive substring match on first name, last name, full name, email and desired role. `%`, `_` and `\` are escaped. Matching is accent-sensitive.
- [x] `status` is optional and must be one of the four values (case-insensitive). Anything else → 422.
- [x] `page` defaults to 1. `page_size` defaults to 25, maximum 100. The order is applied date descending (nulls last), then id. `total` is the scoped count.
- [x] UI: a search box debounced at about 300 ms, a status dropdown offering exactly the four statuses, and a pager. The page resets to 1 when the Recruiter, search or status changes. Loading, empty and error states are shown.
- [x] Tests: search narrows within Scope (Caleb searching for a PH-MNL name gets nothing), and a literal `%` doesn't match everything.
- [x] Tests: the C-1036 DROP payload sent through `search=` returns normally and leaves the table intact.
- [x] Tests: an invalid status → 422; pagination and the scoped `total` are correct.
