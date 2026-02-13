"""dashboard project events table

Revision ID: 20260213_0005
Revises: 20260213_0004
Create Date: 2026-02-13 16:45:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260213_0005"
down_revision = "20260213_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default="info"),
        sa.Column("phase", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "payload",
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
    op.create_index("ix_project_events_user_id", "project_events", ["user_id"], unique=False)
    op.create_index("ix_project_events_project_id", "project_events", ["project_id"], unique=False)
    op.create_index("ix_project_events_event_type", "project_events", ["event_type"], unique=False)
    op.create_index("ix_project_events_priority", "project_events", ["priority"], unique=False)
    op.create_index("ix_project_events_phase", "project_events", ["phase"], unique=False)
    op.create_index("ix_project_events_created_at", "project_events", ["created_at"], unique=False)
    op.create_index(
        "ix_project_events_user_created_at",
        "project_events",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_project_events_project_created_at",
        "project_events",
        ["project_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_project_events_project_created_at", table_name="project_events")
    op.drop_index("ix_project_events_user_created_at", table_name="project_events")
    op.drop_index("ix_project_events_created_at", table_name="project_events")
    op.drop_index("ix_project_events_phase", table_name="project_events")
    op.drop_index("ix_project_events_priority", table_name="project_events")
    op.drop_index("ix_project_events_event_type", table_name="project_events")
    op.drop_index("ix_project_events_project_id", table_name="project_events")
    op.drop_index("ix_project_events_user_id", table_name="project_events")
    op.drop_table("project_events")
