# Notes

## Merge and conflict rules (ADR-0001)

- **Identity** is the normalized email. The Legacy ID (`candidate_id`) is stored, unique and secondary.
- **First-seen wins.** A later row with the same email Merges, filling only the stored Candidate's null fields. A degraded later row (e.g. name "A.") never overwrites anything. Rows already in the database count as first-seen, so a re-import changes nothing (0 imported, 43 merged).
- **ID Collision.** A row that would create a *new* Candidate with a Legacy ID that a different email already owns is rejected (`candidate_id collision`). If the row's email matches a Candidate, the email wins and the row Merges, whatever its Legacy ID.
- **Every row is accounted for.** Each row is imported, Merged (reported with `merged_into`) or rejected with *all* of its reasons. `row` counts CSV records (header excluded), so a multi-line note doesn't shift the numbers. The whole import is one transaction, with bulk lookups and batched writes.
- **Result for the provided CSV:** 40 imported, 3 merged, 10 rejected.

## Normalization rules

All values are trimmed, and blank becomes null.

- **Required fields:** `candidate_id`, email, first and last name, Region and status.
- **Email:** lowercased, then validated (offline). It is never repaired (`[at]` is rejected), and there is no Gmail dot or `+tag` aliasing.
- **Region:** uppercased, with spaces, `-` and `_` stripped, then matched exactly against the six codes (`us-mw`, `USW` and ` CO-BOG ` are all accepted). There is no fuzzy matching.
- **Status:** one of `active`, `screening`, `interviewing` or `withdrawn`, case-insensitive. There is no typo correction (`actve` is rejected).
- **Applied date:** `YYYY-MM-DD`, `MM/DD/YYYY` or `DD-Mon-YYYY` (English month). Impossible dates are rejected. A blank date becomes null.
- **Salary:** `$`, `,` and spaces are stripped, and an optional `k` multiplies by 1000. The result must be a positive integer; otherwise the salary becomes null and the row is still imported.
- **Names:** NFC-normalized, 1 to 100 characters, made of Unicode letters, combining marks, space, `'`, `-` and `.`.
- **Phone, role, source and notes:** stored verbatim after trimming. SQL-looking text is stored as inert text, because every query is parameterized.
- **Upload:** a file over 5 MB → 413. Invalid UTF-8 or missing columns → 400. A BOM is accepted.

## Simplifications and deviations

- **Dates are US order only.** `03/04/2026` means March 4. A day-first format can't be told apart from it.
- **No salary currency.** Salaries are bare integers, and no currency is stored.
- **Phone is not validated.** It is stored as given, because a bad parse would lose a contact.
- **A missing `candidate_id` is a Rejection.** Every Candidate keeps a link back to the source system.
- **RLS has an owner-only policy.** RLS is forced on `candidates`, which binds the table owner too. The owner role therefore has an unrestricted policy (`TO` owner) so the import can see and Merge into every row. Every read, including the roster and the `X-Recruiter-Id` lookup, goes through `techforce_app`, which has no BYPASSRLS. With no Recruiter context set, it sees zero rows.
- **Identity is a header.** The `X-Recruiter-Id` header stands in for real authentication. A missing header → 401, and an unknown ID → 403.

## Why the import is Admin-only

During planning we left the import open, reasoning that the worst case was "anyone can add Candidates". Then the blank-fill Merge landed, and an AI security review pointed out a problem: an open import lets any caller write a salary, phone or notes into *another* person's existing record, just by knowing their email. We made the import Admin-only. A missing header → 401, and an unknown or non-Admin Recruiter → 403. The tests were written first. A decision that was safe on its own became unsafe once it was combined with a later feature.

<!-- DRAFT: candidate to review and personalize -->
## AI usage log

**What I delegated:**
- Implementation, ticket by ticket, to Claude Code agents, test-first, in separate git worktrees.
- Library lookups (via Context7 docs).
- Security review.
- The e2e Playwright suite.

**What I deliberately kept:**
- I ran the design grilling, and I made every rule decision: identity by email, first-seen wins, ID Collision, the date formats, the soft salary, RLS over application filters, and the four statuses. The agents implemented those rules; they didn't choose them.

**Concrete corrections through AI-code-review:**
- **Open import → Admin-only.** See above.
- **Owner locked out by FORCE RLS.** A non-superuser owner would have seen zero rows and failed every import. The fix was the owner-only policy. Also, the compose superuser bypasses RLS entirely, so reads had to move to `techforce_app`.
- **csv field limit.** Python's `csv` caps fields at 128 KiB, so a legal 5 MB file with one long note returned a 500. The exactly-5 MB boundary test found it.
- **Over-permissive date type.** Pydantic's `date` accepted Unix timestamps. Dates are now parsed only in the three agreed formats, with a fixed English month table (`strptime` is locale-dependent).
- **Bad test fixtures.** An accent test was wrong: `Tomas` matched `tomas.herrera@gmail.com` through the email column. Hand-copied CSV rows had also drifted from the file. Fixtures are now copied verbatim and checked with grep.
- **UI bug found by driving the app.** The build didn't catch it: going back to earlier filters revived their old page number.
- **Stale e2e totals.** The e2e totals were written against a dirty shared database (Caleb showed 19 Candidates). The clean run proved the real number is 18.

**Manually Identified:**
- Identified that there were no make scripts that make the setup easier to run on a fresh machine.


## What I'd do next

- **Phones:** E.164 normalization (libphonenumber), with a per-Region default country.
- **Search:** accent-insensitive search with `unaccent` and a trigram index.
- **Authentication:** real authentication (OIDC) mapping users to Recruiters, replacing the header.
- **Statuses:** more statuses (offer, hired, rejected) as a lookup table, not an enum.
- **Salary currency:** stored per Region.
- **Import history:** a persisted Import Report history and an upload page in the UI.
