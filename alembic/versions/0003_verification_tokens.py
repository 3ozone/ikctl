"""T-34.8: tabla verification_tokens con índices.

Revision ID: 0003_verification_tokens
Revises: 0002_refresh_tokens
Create Date: 2026-03-06
"""
from alembic import op
import sqlalchemy as sa

revision: str = "0003_verification_tokens"
down_revision: str | None = "0002_refresh_tokens"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Crea tabla verification_tokens con índices sobre token, type, expires_at y user_id."""
    op.create_table(
        "verification_tokens",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("token", sa.String(500), unique=True, nullable=False),
        sa.Column("token_type", sa.String(50), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_verification_tokens_token", "verification_tokens", ["token"], unique=True
    )
    op.create_index("ix_verification_tokens_user_id",
                    "verification_tokens", ["user_id"])
    op.create_index("ix_verification_tokens_type",
                    "verification_tokens", ["token_type"])
    op.create_index(
        "ix_verification_tokens_expires_at", "verification_tokens", [
            "expires_at"]
    )


def downgrade() -> None:
    """Elimina tabla verification_tokens y sus índices."""
    op.drop_index("ix_verification_tokens_expires_at",
                  table_name="verification_tokens")
    op.drop_index("ix_verification_tokens_type",
                  table_name="verification_tokens")
    op.drop_index("ix_verification_tokens_user_id",
                  table_name="verification_tokens")
    op.drop_index("ix_verification_tokens_token",
                  table_name="verification_tokens")
    op.drop_table("verification_tokens")
