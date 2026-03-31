"""T-38: tabla credentials con cifrado AES-256 para campos sensibles.

Revision ID: 0005_credentials
Revises: 0004_password_history
Create Date: 2026-03-29
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0005_credentials"
down_revision: str | None = "0004_password_history"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Crea tabla credentials con campos cifrados y sus índices."""
    op.create_table(
        "credentials",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("password_encrypted", sa.String(2048), nullable=True),
        sa.Column("private_key_encrypted", sa.String(8192), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_credentials_user_id", "credentials", ["user_id"])
    op.create_index("ix_credentials_type", "credentials", ["type"])


def downgrade() -> None:
    """Elimina tabla credentials y sus índices."""
    op.drop_index("ix_credentials_type", table_name="credentials")
    op.drop_index("ix_credentials_user_id", table_name="credentials")
    op.drop_table("credentials")
