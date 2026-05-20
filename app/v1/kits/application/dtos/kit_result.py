"""DTO para resultado de operaciones sobre kits."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class KitResult:
    """Resultado de consultar un kit descubierto en un repositorio Git."""

    kit_id: str
    user_id: str
    repository_id: str
    path_in_repo: str
    name: str
    description: str
    version: str
    tags: list[str]
    values: dict
    debug_level: str
    sync_status: str
    last_synced_at: Optional[datetime]
    last_commit_sha: Optional[str]
    sync_error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
