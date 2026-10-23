"""Create candidates and recruiters, seed the Recruiter roster.

Revision ID: 0001
Revises:
Create Date: 2026-10-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

REGIONS = ("US-MW", "US-NE", "US-SE", "US-W", "PH-MNL", "CO-BOG")
STATUSES = ("active", "screening", "interviewing", "withdrawn")

# From recruiters.csv. Dana's "*" makes her an Admin.
ROSTER = [
    ("R-101", "Dana Whitmore", "dana.whitmore@techforce-demo.com", "admin", ["*"]),
    ("R-102", "Caleb Nguyen", "caleb.nguyen@techforce-demo.com", "recruiter", ["US-MW", "US-NE"]),
    ("R-103", "Marisol Vega", "marisol.vega@techforce-demo.com", "recruiter", ["PH-MNL", "CO-BOG"]),
    ("R-104", "Jordan Blake", "jordan.blake@techforce-demo.com", "recruiter", ["US-W", "US-SE"]),
    ("R-105", "Tessa Iqbal", "tessa.iqbal@techforce-demo.com", "recruiter", ["US-NE"]),
]


def _in_list(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def upgrade() -> None:
    recruiters = op.create_table(
        "recruiters",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("full_name", sa.Text, nullable=False),
        sa.Column("email", sa.Text, nullable=False, unique=True),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("regions", ARRAY(sa.Text), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'recruiter')", name="recruiters_role_check"),
    )

    op.create_table(
        "candidates",
        sa.Column("id", sa.BigInteger, sa.Identity(always=True), primary_key=True),
        sa.Column("legacy_id", sa.Text, nullable=False),
        sa.Column("first_name", sa.Text, nullable=False),
        sa.Column("last_name", sa.Text, nullable=False),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("phone", sa.Text),
        sa.Column("region", sa.Text, nullable=False),
        sa.Column("desired_role", sa.Text),
        sa.Column("salary", sa.Integer),
        sa.Column("applied_date", sa.Date),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("source", sa.Text),
        sa.Column("notes", sa.Text),
        sa.UniqueConstraint("email", name="candidates_email_key"),
        sa.UniqueConstraint("legacy_id", name="candidates_legacy_id_key"),
        sa.CheckConstraint("email = lower(email)", name="candidates_email_normalized_check"),
        sa.CheckConstraint(_in_list("region", REGIONS), name="candidates_region_check"),
        sa.CheckConstraint(_in_list("status", STATUSES), name="candidates_status_check"),
        sa.CheckConstraint("salary > 0", name="candidates_salary_positive_check"),
    )

    op.bulk_insert(
        recruiters,
        [
            {"id": id_, "full_name": name, "email": email, "role": role, "regions": regions}
            for id_, name, email, role, regions in ROSTER
        ],
    )


def downgrade() -> None:
    op.drop_table("candidates")
    op.drop_table("recruiters")
