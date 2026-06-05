"""R8: backfill kit_ids null y values empty dict en targets existentes.

Revision ID: 0017_pipelines_targets_add_target_roles
Revises: 0016_pipeline_executions
Create Date: 2026-06-05
"""
import json

import sqlalchemy as sa
from alembic import op

revision: str = "0017_pipelines_targets_add_target_roles"
down_revision: str | None = "0016_pipeline_executions"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Backfill kit_ids y values en targets existentes que carezcan de ellos."""
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, targets FROM pipelines")).fetchall()
    for pid, targets_raw in rows:
        if not targets_raw:
            continue
        targets = json.loads(targets_raw) if isinstance(targets_raw, str) else targets_raw
        modified = False
        for t in targets:
            if "kit_ids" not in t:
                t["kit_ids"] = None
                modified = True
            if "values" not in t:
                t["values"] = {}
                modified = True
        if modified:
            conn.execute(
                sa.text("UPDATE pipelines SET targets = :targets WHERE id = :id"),
                {"targets": json.dumps(targets, ensure_ascii=False), "id": pid},
            )


def downgrade() -> None:
    """Revertir: eliminar kit_ids y values de cada target."""
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, targets FROM pipelines")).fetchall()
    for pid, targets_raw in rows:
        if not targets_raw:
            continue
        targets = json.loads(targets_raw) if isinstance(targets_raw, str) else targets_raw
        modified = False
        for t in targets:
            if "kit_ids" in t:
                del t["kit_ids"]
                modified = True
            if "values" in t:
                del t["values"]
                modified = True
        if modified:
            conn.execute(
                sa.text("UPDATE pipelines SET targets = :targets WHERE id = :id"),
                {"targets": json.dumps(targets, ensure_ascii=False), "id": pid},
            )
