"""Añade columna role a tabla users.

Revision ID: 0009_user_role
Revises: 0008_group_members
Create Date: 2026-04-05
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0009_user_role"
down_revision: str | None = "0008_group_members"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Añade columna role a users con valor por defecto 'user'."""
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.Enum("user", "admin", name="user_role"),
            nullable=False,
            server_default="user",
        ),
    )


def downgrade() -> None:
    """Elimina columna role de users y el tipo enum user_role."""
    op.drop_column("users", "role")
    op.execute("DROP TYPE IF EXISTS user_role")
