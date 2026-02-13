"""supplier memory interaction history

Revision ID: 20260213_0003
Revises: 20260213_0002
Create Date: 2026-02-13 09:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260213_0003"
down_revision = "20260213_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_suppliers_email", "suppliers", ["email"], unique=False)
    op.create_index("ix_suppliers_website", "suppliers", ["website"], unique=False)
    op.create_index("ix_suppliers_country", "suppliers", ["country"], unique=False)

    op.create_table(
        "supplier_interactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("interaction_type", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="system"),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_supplier_interactions_supplier_id", "supplier_interactions", ["supplier_id"], unique=False)
    op.create_index("ix_supplier_interactions_project_id", "supplier_interactions", ["project_id"], unique=False)
    op.create_index(
        "ix_supplier_interactions_interaction_type",
        "supplier_interactions",
        ["interaction_type"],
        unique=False,
    )
    op.create_index("ix_supplier_interactions_created_at", "supplier_interactions", ["created_at"], unique=False)
    op.create_index(
        "ix_supplier_interactions_supplier_created",
        "supplier_interactions",
        ["supplier_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_supplier_interactions_supplier_created", table_name="supplier_interactions")
    op.drop_index("ix_supplier_interactions_created_at", table_name="supplier_interactions")
    op.drop_index("ix_supplier_interactions_interaction_type", table_name="supplier_interactions")
    op.drop_index("ix_supplier_interactions_project_id", table_name="supplier_interactions")
    op.drop_index("ix_supplier_interactions_supplier_id", table_name="supplier_interactions")
    op.drop_table("supplier_interactions")

    op.drop_index("ix_suppliers_country", table_name="suppliers")
    op.drop_index("ix_suppliers_website", table_name="suppliers")
    op.drop_index("ix_suppliers_email", table_name="suppliers")
