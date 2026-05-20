"""DTO para resultado de sincronización de un repositorio Git."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RepositorySyncResult:
    """Resultado de ejecutar SyncRepository.

    La sincronización siempre devuelve 200 — si falla, sync_status
    es 'sync_error' con el mensaje de error. Nunca lanza 500.
    """

    repository_id: str
    sync_status: str
    last_commit_sha: Optional[str]
    sync_error_message: Optional[str]
    kits_created: int
    kits_updated: int
    kits_deleted: int
