"""DTO para resultado de operaciones sobre repositorios Git."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class RepositoryResult:
    """Resultado de crear o actualizar un repositorio Git."""

    repository_id: str
    user_id: str
    url: str
    ref: str
    credential_id: Optional[str]
    sync_status: str
    last_synced_at: Optional[datetime]
    last_commit_sha: Optional[str]
    sync_error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
