"""create automotive procurement tables

Revision ID: 20260215_0008
Revises: 20260214_0007
Create Date: 2026-02-15 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260215_0008"
down_revision = "20260214_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- automotive_projects ---
    op.create_table(
        "automotive_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("org_id", sa.String(255), server_default="default", nullable=False),
        sa.Column("raw_request", sa.Text(), server_default="", nullable=False),
        sa.Column("parsed_requirement", postgresql.JSON(), nullable=True),
        sa.Column("current_stage", sa.String(50), server_default="parse", nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("discovery_result", postgresql.JSON(), nullable=True),
        sa.Column("qualification_result", postgresql.JSON(), nullable=True),
        sa.Column("comparison_matrix", postgresql.JSON(), nullable=True),
        sa.Column("intelligence_reports", postgresql.JSON(), nullable=True),
        sa.Column("rfq_result", postgresql.JSON(), nullable=True),
        sa.Column("quote_ingestion", postgresql.JSON(), nullable=True),
        sa.Column("approvals", postgresql.JSON(), server_default="{}", nullable=False),
        sa.Column("human_overrides", postgresql.JSON(), server_default="{}", nullable=False),
        sa.Column(
            "weight_profile",
            postgresql.JSON(),
            server_default='{"capability":0.25,"quality":0.25,"geography":0.20,"financial":0.15,"scale":0.10,"reputation":0.05}',
            nullable=False,
        ),
        sa.Column("buyer_company", sa.String(255), server_default="", nullable=False),
        sa.Column("buyer_contact_name", sa.String(255), server_default="", nullable=False),
        sa.Column("buyer_contact_email", sa.String(255), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # --- automotive_project_events ---
    op.create_table(
        "automotive_project_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("automotive_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("data", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_auto_events_project_id", "automotive_project_events", ["project_id"])

    # --- automotive_suppliers ---
    op.create_table(
        "automotive_suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("automotive_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company_name", sa.String(500), nullable=False),
        sa.Column("headquarters", sa.String(500), server_default="", nullable=False),
        sa.Column("website", sa.String(1000), nullable=True),
        sa.Column("phone", sa.String(100), nullable=True),
        sa.Column("email", sa.String(500), nullable=True),
        sa.Column("qualification_status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("iatf_status", sa.String(50), server_default="unknown", nullable=False),
        sa.Column("financial_risk", sa.String(50), server_default="unknown", nullable=False),
        sa.Column("profile_data", postgresql.JSON(), nullable=True),
        sa.Column("composite_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_auto_suppliers_project_id", "automotive_suppliers", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_auto_suppliers_project_id", table_name="automotive_suppliers")
    op.drop_table("automotive_suppliers")
    op.drop_index("ix_auto_events_project_id", table_name="automotive_project_events")
    op.drop_table("automotive_project_events")
    op.drop_table("automotive_projects")
