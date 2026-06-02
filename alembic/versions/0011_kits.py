"""T-25: tabla kits para el módulo kits (FK a repositories CASCADE).

Revision ID: 0011_kits
Revises: 0010_repositories
Create Date: 2026-05-26
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0011_kits"
down_revision: str | None = "0010_repositories"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Crea tabla kits con FK a repositories y sus índices."""
    op.create_table(
        "kits",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column(
            "repository_id",
            sa.String(36),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path_in_repo", sa.String(1024), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(2048), nullable=False, server_default=""),
        sa.Column("version", sa.String(50), nullable=False, server_default=""),
        sa.Column("tags", sa.Text(), nullable=False),
        sa.Column("values", sa.Text(), nullable=False),
        sa.Column("debug_level", sa.String(20), nullable=False, server_default="info"),
        sa.Column("sync_status", sa.String(20), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("last_commit_sha", sa.String(40), nullable=True),
        sa.Column("sync_error_message", sa.String(2048), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_kits_user_id", "kits", ["user_id"])
    op.create_index("ix_kits_repository_id", "kits", ["repository_id"])
    op.create_index("ix_kits_sync_status", "kits", ["sync_status"])
    op.create_index("ix_kits_is_deleted", "kits", ["is_deleted"])


def downgrade() -> None:
    """Elimina tabla kits y sus índices."""
    op.drop_index("ix_kits_is_deleted", table_name="kits")
    op.drop_index("ix_kits_sync_status", table_name="kits")
    op.drop_index("ix_kits_repository_id", table_name="kits")
    op.drop_index("ix_kits_user_id", table_name="kits")
    op.drop_table("kits")
