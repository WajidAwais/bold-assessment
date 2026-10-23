# 04: Merge, ID Collision and idempotent re-import

**What to build:** Rows that belong to an existing Candidate (same normalized email) Merge into it rather than creating a duplicate: the first-seen record wins, and later rows only fill blanks. A row that would reuse another person's Legacy ID is rejected as an ID Collision. The database counts as first-seen, so importing the same file twice changes nothing. Importing the provided CSV gives exactly 40 imported, 3 merged and 10 rejected. See ADR-0001.

**Blocked by:** 03: Validation, normalization and Rejections

**Status:** ready-for-agent

- [ ] Existing emails and Legacy IDs are looked up in bulk, in a single query (no per-row lookups). Inserts and blank-fills are batched, all inside one transaction.
- [ ] First-seen wins within a file and against the database. Later rows fill only null fields.
- [ ] ID Collision: a row that would create a new Candidate with a Legacy ID owned by a different email is rejected with `candidate_id collision`.
- [ ] When a row's email matches Candidate X and its Legacy ID belongs to Candidate Y, it Merges into X by email; this is not a collision.
- [ ] The Import Report's `merges` list holds `{row, candidate_id, merged_into}` for every Merge.
- [ ] Unit tests: first-seen Merge, blank-fill, ID Collision and email-wins.
- [ ] Integration test: the real CSV gives exactly **40 imported / 3 merged / 10 rejected**:
  - Merges: rows 31 (C-1004 → C-1004), 32 (C-1031 → C-1001), 33 (C-1032 → C-1016).
  - Rejections: rows 34, 35, 36, 37, 41, 46, 48, 49, 52 (C-1010 collision) and 53, each with the expected reason.
  - Amara Diallo keeps the first name "Amara".
- [ ] Integration test: re-importing the same file → `imported: 0, merged: 43`, with the same 10 rejections.
