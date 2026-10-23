"""Table metadata for SQLAlchemy Core. The schema itself is owned by Alembic."""

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    Integer,
    MetaData,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY

metadata = MetaData()

recruiters = Table(
    "recruiters",
    metadata,
    Column("id", Text, primary_key=True),
    Column("full_name", Text, nullable=False),
    Column("email", Text, nullable=False, unique=True),
    Column("role", Text, nullable=False),
    # Canonical Region codes, or ["*"] for an Admin.
    Column("regions", ARRAY(Text), nullable=False),
)

candidates = Table(
    "candidates",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("legacy_id", Text, nullable=False, unique=True),
    Column("first_name", Text, nullable=False),
    Column("last_name", Text, nullable=False),
    Column("email", Text, nullable=False, unique=True),
    Column("phone", Text),
    Column("region", Text, nullable=False),
    Column("desired_role", Text),
    Column("salary", Integer),
    Column("applied_date", Date),
    Column("status", Text, nullable=False),
    Column("source", Text),
    Column("notes", Text),
)
