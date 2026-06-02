"""T-22/T-23/T-24: tablas operations y server_kit_file_cache para el módulo operations.

Revision ID: 0012_operations
Revises: 0011_kits
Create Date: 2026-05-29
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0012_operations"
down_revision: str | None = "0011_kits"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Crea tabla operations y tabla server_kit_file_cache con sus índices."""
    # ── tabla operations ──────────────────────────────────────────────────
    op.create_table(
        "operations",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("server_id", sa.String(36), nullable=False),
        sa.Column("kit_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("debug_level", sa.String(20), nullable=False, server_default="none"),
        sa.Column("output", sa.Text(), nullable=False, server_default=""),
        sa.Column("backup_files", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_operations_user_id", "operations", ["user_id"])
    op.create_index("ix_operations_server_id", "operations", ["server_id"])
    op.create_index("ix_operations_kit_id", "operations", ["kit_id"])
    op.create_index("ix_operations_status", "operations", ["status"])

    # ── tabla server_kit_file_cache ───────────────────────────────────────
    op.create_table(
        "server_kit_file_cache",
        sa.Column("server_id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("kit_id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("filename", sa.String(500), primary_key=True, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_server_kit_file_cache_server_kit",
        "server_kit_file_cache",
        ["server_id", "kit_id"],
    )


def downgrade() -> None:
    """Elimina tabla server_kit_file_cache y tabla operations con sus índices."""
    # ── eliminar server_kit_file_cache ────────────────────────────────────
    op.drop_index("ix_server_kit_file_cache_server_kit", table_name="server_kit_file_cache")
    op.drop_table("server_kit_file_cache")

    # ── eliminar operations ───────────────────────────────────────────────
    op.drop_index("ix_operations_status", table_name="operations")
    op.drop_index("ix_operations_kit_id", table_name="operations")
    op.drop_index("ix_operations_server_id", table_name="operations")
    op.drop_index("ix_operations_user_id", table_name="operations")
    op.drop_table("operations")
