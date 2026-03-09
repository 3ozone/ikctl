"""T-34.9: tabla password_history con índice compuesto.

Revision ID: 0004_password_history
Revises: 0003_verification_tokens
Create Date: 2026-03-06
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0004_password_history"
down_revision: str | None = "0003_verification_tokens"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Crea tabla password_history con índice compuesto (user_id, created_at DESC)."""
    op.create_table(
        "password_history",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_password_history_user_created",
        "password_history",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    """Elimina tabla password_history y su índice."""
    op.drop_index("ix_password_history_user_created",
                  table_name="password_history")
    op.drop_table("password_history")
