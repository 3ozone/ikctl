"""T-25: tabla pipeline_executions para el módulo pipelines.

Revision ID: 0016_pipeline_executions
Revises: 0015_pipelines
Create Date: 2026-06-03
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0016_pipeline_executions"
down_revision: str | None = "0015_pipelines"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Crea tabla pipeline_executions con sus índices."""
    op.create_table(
        "pipeline_executions",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("pipeline_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("operation_ids", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("snapshot", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_pipeline_executions_pipeline_id", "pipeline_executions", ["pipeline_id"])
    op.create_index("ix_pipeline_executions_user_id", "pipeline_executions", ["user_id"])
    op.create_index("ix_pipeline_executions_status", "pipeline_executions", ["status"])


def downgrade() -> None:
    """Elimina tabla pipeline_executions y sus índices."""
    op.drop_index("ix_pipeline_executions_status", table_name="pipeline_executions")
    op.drop_index("ix_pipeline_executions_user_id", table_name="pipeline_executions")
    op.drop_index("ix_pipeline_executions_pipeline_id", table_name="pipeline_executions")
    op.drop_table("pipeline_executions")
