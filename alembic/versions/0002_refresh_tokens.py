"""T-34.7: tabla refresh_tokens con índices.

Revision ID: 0002_refresh_tokens
Revises: 0001_users
Create Date: 2026-03-06
"""
from alembic import op
import sqlalchemy as sa

revision: str = "0002_refresh_tokens"
down_revision: str | None = "0001_users"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Crea tabla refresh_tokens con índices sobre token, user_id y expires_at."""
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("token", sa.String(500), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_refresh_tokens_token",
                    "refresh_tokens", ["token"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_expires_at",
                    "refresh_tokens", ["expires_at"])


def downgrade() -> None:
    """Elimina tabla refresh_tokens y sus índices."""
    op.drop_index("ix_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_token", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
