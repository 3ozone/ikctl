"""Add values and sudo columns to operations table.

Revision ID: 0014
Revises: 0013
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_operations_values_sudo"
down_revision = "0013_kits_file_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("operations", sa.Column("values", sa.TEXT(), nullable=False, server_default="{}"))
    op.add_column("operations", sa.Column("sudo", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")))


def downgrade() -> None:
    op.drop_column("operations", "sudo")
    op.drop_column("operations", "values")