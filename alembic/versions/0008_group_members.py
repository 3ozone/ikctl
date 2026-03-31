"""T-41: tabla group_members con PK compuesta y CASCADE delete.

Revision ID: 0008_group_members
Revises: 0007_groups
Create Date: 2026-03-29
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0008_group_members"
down_revision: str | None = "0007_groups"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Crea tabla group_members con PK compuesta (group_id, server_id) y CASCADE delete."""
    op.create_table(
        "group_members",
        sa.Column(
            "group_id",
            sa.String(36),
            sa.ForeignKey("groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "server_id",
            sa.String(36),
            sa.ForeignKey("servers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("group_id", "server_id"),
    )


def downgrade() -> None:
    """Elimina tabla group_members."""
    op.drop_table("group_members")
