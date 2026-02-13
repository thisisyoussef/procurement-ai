"""runtime projects and growth tables

Revision ID: 20260213_0002
Revises: 20260213_0001
Create Date: 2026-02-13 01:48:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260213_0002"
down_revision = "20260213_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("product_description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="parsing"),
        sa.Column("current_stage", sa.String(length=64), nullable=False, server_default="parsing"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_runtime_projects_user_id", "runtime_projects", ["user_id"], unique=False)
    op.create_index("ix_runtime_projects_status", "runtime_projects", ["status"], unique=False)
    op.create_index("ix_runtime_projects_current_stage", "runtime_projects", ["current_stage"], unique=False)

    op.create_table(
        "landing_leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=500), nullable=False, unique=True),
        sa.Column("sourcing_note", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False, server_default="landing_early_access"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_landing_leads_email", "landing_leads", ["email"], unique=True)

    op.create_table(
        "analytics_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("event_name", sa.String(length=120), nullable=False),
        sa.Column("session_id", sa.String(length=120), nullable=True),
        sa.Column("path", sa.String(length=500), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_analytics_events_event_name", "analytics_events", ["event_name"], unique=False)
    op.create_index("ix_analytics_events_created_at", "analytics_events", ["created_at"], unique=False)
    op.create_index("ix_analytics_events_project_id", "analytics_events", ["project_id"], unique=False)
    op.create_index("ix_analytics_events_event_name_created_at", "analytics_events", ["event_name", "created_at"], unique=False)
    op.create_index("ix_analytics_events_project_id_created_at", "analytics_events", ["project_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_analytics_events_project_id_created_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_event_name_created_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_project_id", table_name="analytics_events")
    op.drop_index("ix_analytics_events_created_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_event_name", table_name="analytics_events")
    op.drop_table("analytics_events")

    op.drop_index("ix_landing_leads_email", table_name="landing_leads")
    op.drop_table("landing_leads")

    op.drop_index("ix_runtime_projects_current_stage", table_name="runtime_projects")
    op.drop_index("ix_runtime_projects_status", table_name="runtime_projects")
    op.drop_index("ix_runtime_projects_user_id", table_name="runtime_projects")
    op.drop_table("runtime_projects")
