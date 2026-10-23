# Candidate identity is the normalized email, not the legacy candidate_id

The legacy export reuses `candidate_id`s (C-1010 belongs to two different people) and gives one person several IDs (C-1001/C-1031, C-1016/C-1032), so we identify a Candidate by their trimmed, lowercased email and keep `candidate_id` only as a unique Legacy ID. Rows whose email matches an existing Candidate merge into it, first-seen wins and later rows only fill blanks, and the database counts as first-seen, so re-imports are idempotent. A row that would create a new Candidate with a Legacy ID already owned by a different email is rejected as an ID Collision rather than overwriting that person.

## Considered Options

- **Identity by `candidate_id`**: rejected. C-1031/C-1032 would become separate people sharing one email, and Becca Storm (C-1010) would overwrite Sofía Cárdenas.
- **Last-seen wins / newest applied_date wins**: rejected. C-1032's degraded name "A." would overwrite "Amara". Newer data isn't necessarily better.

## Consequences

- Email is required. A row without a valid email has no identity and is rejected.
- If an email matches Candidate X but the Legacy ID belongs to Candidate Y, email wins: the row merges into X and its Legacy ID is reported in `merges`, not raised as a collision.
- Provider-specific aliasing (Gmail dots, `+tags`) is deliberately not collapsed.
