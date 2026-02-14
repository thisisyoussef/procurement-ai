"""add business profile fields to users

Revision ID: 20260213_0006
Revises: 20260213_0005
Create Date: 2026-02-13 21:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260213_0006"
down_revision = "20260213_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("job_title", sa.String(length=300), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("company_website", sa.String(length=1000), nullable=True))
    op.add_column("users", sa.Column("business_address", sa.String(length=1000), nullable=True))
    op.add_column("users", sa.Column("company_description", sa.String(length=2000), nullable=True))
    op.add_column(
        "users",
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed")
    op.drop_column("users", "company_description")
    op.drop_column("users", "business_address")
    op.drop_column("users", "company_website")
    op.drop_column("users", "phone")
    op.drop_column("users", "job_title")
