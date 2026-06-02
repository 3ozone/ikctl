"""T-24: tabla repositories para el módulo kits.

Revision ID: 0010_repositories
Revises: 0009_user_role
Create Date: 2026-05-26
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0010_repositories"
down_revision: str | None = "0009_user_role"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Crea tabla repositories con sus índices."""
    op.create_table(
        "repositories",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("ref", sa.String(255), nullable=False),
        sa.Column("credential_id", sa.String(36), nullable=True),
        sa.Column("sync_status", sa.String(20), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("last_commit_sha", sa.String(40), nullable=True),
        sa.Column("sync_error_message", sa.String(2048), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_repositories_user_id", "repositories", ["user_id"])
    op.create_index("ix_repositories_sync_status", "repositories", ["sync_status"])
    op.create_index("ix_repositories_is_deleted", "repositories", ["is_deleted"])


def downgrade() -> None:
    """Elimina tabla repositories y sus índices."""
    op.drop_index("ix_repositories_is_deleted", table_name="repositories")
    op.drop_index("ix_repositories_sync_status", table_name="repositories")
    op.drop_index("ix_repositories_user_id", table_name="repositories")
    op.drop_table("repositories")
