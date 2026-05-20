"""Value Object SyncStatus."""
from dataclasses import dataclass

from app.v1.kits.domain.exceptions.repository import InvalidSyncStatusError

VALID_SYNC_STATUSES = {"never_synced", "synced", "sync_error"}


@dataclass(frozen=True)
class SyncStatus:
    """Estado de sincronización. Valores permitidos: never_synced, synced, sync_error."""

    value: str

    def __post_init__(self) -> None:
        if self.value not in VALID_SYNC_STATUSES:
            raise InvalidSyncStatusError()
