"""Scope Candidates to the Recruiter with forced Row-Level Security (ADR-0002).

Creates the non-owner ``techforce_app`` role (no BYPASSRLS) that serves every
Candidate read, and enables and FORCES RLS on ``candidates``. The scope policy
admits a row when the Recruiter named by the transaction-local
``app.recruiter_id`` setting is an Admin or has the row's Region. With no
setting, ``current_setting(..., true)`` is NULL (or '' after a reset), no
Recruiter matches, and no rows are visible: reads fail closed.

Roles are cluster-wide, so the role is created idempotently: several databases
on one cluster (e.g. parallel test databases) can each run this migration.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-23
"""

from alembic import op
from sqlalchemy.engine import make_url

from app.config import Settings

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

APP_ROLE = "techforce_app"


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    app_url = make_url(Settings().app_database_url)
    if app_url.username != APP_ROLE:
        raise RuntimeError(f"APP_DATABASE_URL must connect as {APP_ROLE}")
    password = _sql_literal(app_url.password or "")

    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
                CREATE ROLE {APP_ROLE} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD {password};
            ELSE
                ALTER ROLE {APP_ROLE} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD {password};
            END IF;
        END
        $$
        """
    )
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
    op.execute(f"GRANT SELECT ON candidates, recruiters TO {APP_ROLE}")

    op.execute("ALTER TABLE candidates ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE candidates FORCE ROW LEVEL SECURITY")

    # Applies to every role, so any reader other than the owner is scoped too.
    op.execute(
        """
        CREATE POLICY candidates_recruiter_scope ON candidates
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM recruiters r
                WHERE r.id = current_setting('app.recruiter_id', true)
                  AND (r.role = 'admin' OR candidates.region = ANY (r.regions))
            )
        )
        """
    )
    # FORCE subjects the owner to RLS as well. The import runs as the owner and
    # must see and write every Candidate (Merge and ID Collision detection), so
    # the owner, and only the owner, gets an explicit unrestricted policy. A
    # superuser bypasses RLS anyway; this keeps a non-superuser owner working.
    op.execute(
        """
        DO $$
        BEGIN
            EXECUTE format(
                'CREATE POLICY candidates_owner_import ON candidates TO %I '
                'USING (true) WITH CHECK (true)',
                current_user
            );
        END
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS candidates_owner_import ON candidates")
    op.execute("DROP POLICY IF EXISTS candidates_recruiter_scope ON candidates")
    op.execute("ALTER TABLE candidates NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE candidates DISABLE ROW LEVEL SECURITY")
    op.execute(f"REVOKE SELECT ON candidates, recruiters FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {APP_ROLE}")
    # The role itself is cluster-wide and may serve other databases; keep it.
