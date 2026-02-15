"""add buyer context and sourcing profile columns

Revision ID: 20260214_0007
Revises: 20260213_0006
Create Date: 2026-02-14 19:15:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260214_0007"
down_revision = "20260213_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("sourcing_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("users", sa.Column("default_buyer_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("runtime_projects", sa.Column("buyer_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("runtime_projects", "buyer_context")
    op.drop_column("users", "default_buyer_context")
    op.drop_column("users", "sourcing_profile")
