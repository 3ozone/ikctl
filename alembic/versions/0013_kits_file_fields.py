"""T-Kits: añade upload_files, pipeline_files, backup_files a tabla kits.

Revision ID: 0013_kits_file_fields
Revises: 0012_operations
Create Date: 2026-05-29
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0013_kits_file_fields"
down_revision: str | None = "0012_operations"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Añade columnas upload_files, pipeline_files y backup_files a la tabla kits."""
    op.add_column(
        "kits",
        sa.Column("upload_files", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "kits",
        sa.Column("pipeline_files", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "kits",
        sa.Column("backup_files", sa.Text(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    """Elimina las columnas upload_files, pipeline_files y backup_files de la tabla kits."""
    op.drop_column("kits", "backup_files")
    op.drop_column("kits", "pipeline_files")
    op.drop_column("kits", "upload_files")
