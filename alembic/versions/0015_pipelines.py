"""T-24: tabla pipelines para el módulo pipelines.

Revision ID: 0015_pipelines
Revises: 0014_operations_values_sudo
Create Date: 2026-06-03
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0015_pipelines"
down_revision: str | None = "0014_operations_values_sudo"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Crea tabla pipelines con sus índices."""
    op.create_table(
        "pipelines",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(2048), nullable=True),
        sa.Column("targets", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("kits", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("values", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("sudo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("debug_level", sa.String(20), nullable=False, server_default="none"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_pipelines_user_id", "pipelines", ["user_id"])
    op.create_index("ix_pipelines_name", "pipelines", ["name"])


def downgrade() -> None:
    """Elimina tabla pipelines y sus índices."""
    op.drop_index("ix_pipelines_name", table_name="pipelines")
    op.drop_index("ix_pipelines_user_id", table_name="pipelines")
    op.drop_table("pipelines")
