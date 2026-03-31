"""T-39: tabla servers con FK a credentials (SET NULL on delete).

Revision ID: 0006_servers
Revises: 0005_credentials
Create Date: 2026-03-29
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0006_servers"
down_revision: str | None = "0005_credentials"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Crea tabla servers con FK a credentials y sus índices."""
    op.create_table(
        "servers",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("host", sa.String(255), nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column(
            "credential_id",
            sa.String(36),
            sa.ForeignKey("credentials.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column("os_id", sa.String(100), nullable=True),
        sa.Column("os_version", sa.String(100), nullable=True),
        sa.Column("os_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_servers_user_id", "servers", ["user_id"])
    op.create_index("ix_servers_status", "servers", ["status"])
    op.create_index("ix_servers_credential_id", "servers", ["credential_id"])


def downgrade() -> None:
    """Elimina tabla servers y sus índices."""
    op.drop_index("ix_servers_credential_id", table_name="servers")
    op.drop_index("ix_servers_status", table_name="servers")
    op.drop_index("ix_servers_user_id", table_name="servers")
    op.drop_table("servers")
