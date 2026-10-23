# 03: Validation, normalization and Rejections

**What to build:** Importing the CSV applies every agreed normalization rule and reports each row that can't become a Candidate as a Rejection, with its record number, Legacy ID and every reason. Bad files are refused before any row is processed. Hostile content is either rejected by the ordinary validation rules or stored as inert text. The rules live in a pure `domain/` layer with no I/O. See the Validation rules section of the spec.

**Blocked by:** 01: Walking skeleton

**Status:** ready-for-agent

- [ ] Pydantic v2 Candidate model. Required: email, first name, last name, Region, status. Everything else is nullable.
- [ ] Email: trimmed, lowercased, `EmailStr` (offline). `[at]`, missing `@` and empty emails are rejected, never repaired.
- [ ] Region: case-, whitespace- and separator-insensitive exact match (`us-mw`, ` CO-BOG `, `USW` → `US-W`). `ZZ-99` and missing Regions are rejected.
- [ ] Status: four-value enum, case-insensitive (`ACTIVE` is accepted). `actve` and `on hold` are rejected.
- [ ] Dates: `YYYY-MM-DD`, `MM/DD/YYYY` or `DD-Mon-YYYY`. Empty → null. `2026-02-30` is rejected.
- [ ] Salary: `$95,000`, `97,500` and `85k` become integers. `negotiable` and empty become null, and the row is not rejected.
- [ ] Names: NFC-normalized, Unicode letter allow-list (apostrophe, hyphen, period and space allowed). C-1036's last name is rejected with `invalid characters in last_name`.
- [ ] Phone, role, source and notes: trimmed, otherwise stored verbatim. Multi-line notes are preserved.
- [ ] Each Rejection is `{row, candidate_id, reason}`: `row` is the 1-based record number (header excluded), and `reason` joins every error with `; ` using the fixed prefixes.
- [ ] File guards: invalid UTF-8 → 400; a BOM is tolerated; missing expected columns → 400 naming them; over 5 MB → 413.
- [ ] Table-driven unit tests over real CSV rows for each rule (including the invalid-email rejection).
- [ ] Integration tests:
  - C-1037's notes payload `' OR '1'='1` round-trips unchanged.
  - The `candidates` table survives the import.
  - The C-1036 DROP payload in notes is stored inertly.
