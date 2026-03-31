"""T-40: tabla groups.

Revision ID: 0007_groups
Revises: 0006_servers
Create Date: 2026-03-29
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0007_groups"
down_revision: str | None = "0006_servers"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Crea tabla groups con índice por user_id."""
    op.create_table(
        "groups",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_groups_user_id", "groups", ["user_id"])


def downgrade() -> None:
    """Elimina tabla groups y su índice."""
    op.drop_index("ix_groups_user_id", table_name="groups")
    op.drop_table("groups")
