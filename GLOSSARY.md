# TechForce Recruiting Operations

A recruiting operations platform: candidates are imported from legacy exports and shown to recruiters only within the regions they cover.

## Language

### Candidates

**Candidate**:
A person seeking a role, identified by their normalized email address. One person is one Candidate, however many legacy records they appear in.
_Avoid_: Applicant, record, profile

**Legacy ID**:
The `candidate_id` a Candidate carried in the legacy export (e.g. `C-1004`). A reference back to the source system, not the Candidate's identity; it must still belong to only one Candidate.
_Avoid_: Candidate ID (as a synonym for identity)

### Import

**Merge**:
Folding an import row into a Candidate that already has the same normalized email, instead of creating a new Candidate. The first-seen Candidate keeps its values; the merged row only fills blanks.
_Avoid_: Dedupe (as a noun), upsert

**Import Report**:
The outcome of one import: how many Candidates were created, how many rows were Merged, and every Rejection with its reason.
_Avoid_: Import log, import result

**ID Collision**:
An import row whose Legacy ID already belongs to a Candidate with a different email. The row is rejected rather than merged.
_Avoid_: Duplicate ID

**Rejection**:
An import row that cannot become or merge into a Candidate, reported back with its row number and reason.
_Avoid_: Skipped row, dropped row

### Access

**Recruiter**:
A user who sees only the Candidates in their Scope.

**Admin**:
A Recruiter whose role is admin, giving visibility of every Candidate and the right to import. The roster shows an Admin's Regions as `*`.
_Avoid_: Superuser

**Scope**:
The set of Candidates a Recruiter may see: those whose Region is among the Recruiter's assigned Regions, or all Candidates for an Admin.
_Avoid_: Visibility, permissions

**Region**:
One of the canonical codes `US-MW`, `US-NE`, `US-SE`, `US-W`, `PH-MNL`, `CO-BOG`. A value that cannot be confidently normalized to one of these is invalid.
_Avoid_: Territory, location
