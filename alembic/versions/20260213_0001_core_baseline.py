"""core baseline tables

Revision ID: 20260213_0001
Revises:
Create Date: 2026-02-13 01:47:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = "20260213_0001"
down_revision = None
branch_labels = None
depends_on = None


project_status = postgresql.ENUM(
    "DRAFT",
    "PARSING",
    "SEARCHING",
    "VERIFYING",
    "QUOTING",
    "COMPARING",
    "COMPLETED",
    "FAILED",
    name="projectstatus",
)


def upgrade() -> None:
    bind = op.get_bind()
    vector_available = bool(
        bind.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector')"
            )
        ).scalar()
    )

    if vector_available:
        # Execute extension creation in autocommit mode so failures don't poison
        # Alembic's migration transaction.
        try:
            with op.get_context().autocommit_block():
                op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        except Exception:
            vector_available = False

    vector_installed = bool(
        bind.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        ).scalar()
    )

    embedding_type = (
        Vector(1536) if vector_installed else postgresql.JSONB(astext_type=sa.Text())
    )

    project_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=500), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=500), nullable=True),
        sa.Column("company_name", sa.String(length=500), nullable=True),
        sa.Column("plan", sa.String(length=50), nullable=False, server_default="free_trial"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("website", sa.String(length=1000), nullable=True),
        sa.Column("email", sa.String(length=500), nullable=True),
        sa.Column("phone", sa.String(length=100), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=200), nullable=True),
        sa.Column("state", sa.String(length=200), nullable=True),
        sa.Column("country", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("categories", postgresql.ARRAY(sa.String(length=200)), nullable=True),
        sa.Column("certifications", postgresql.ARRAY(sa.String(length=200)), nullable=True),
        sa.Column("year_established", sa.Integer(), nullable=True),
        sa.Column("employee_count", sa.String(length=100), nullable=True),
        sa.Column("moq_range", sa.String(length=200), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("verification_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("verification_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False, server_default="manual"),
        sa.Column("google_rating", sa.Float(), nullable=True),
        sa.Column("google_review_count", sa.Integer(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("embedding", embedding_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_suppliers_name", "suppliers", ["name"], unique=False)

    op.create_table(
        "sourcing_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("product_description", sa.Text(), nullable=False),
        sa.Column("parsed_requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", project_status, nullable=False, server_default="DRAFT"),
        sa.Column("agent_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("discovered_suppliers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("verification_results", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("comparison_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("recommendation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sourcing_projects_user_id", "sourcing_projects", ["user_id"], unique=False)

    op.create_table(
        "quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sourcing_projects.id"), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="USD"),
        sa.Column("moq", sa.Integer(), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("payment_terms", sa.Text(), nullable=True),
        sa.Column("shipping_terms", sa.String(length=200), nullable=True),
        sa.Column("certifications_offered", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sample_cost", sa.Float(), nullable=True),
        sa.Column("raw_response_text", sa.Text(), nullable=True),
        sa.Column("parsed_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("quotes")
    op.drop_index("ix_sourcing_projects_user_id", table_name="sourcing_projects")
    op.drop_table("sourcing_projects")
    op.drop_index("ix_suppliers_name", table_name="suppliers")
    op.drop_table("suppliers")
    op.drop_table("users")
    project_status.drop(op.get_bind(), checkfirst=True)
