"""Tests para el Value Object SyncStatus."""
import pytest

from app.v1.kits.domain.value_objects.sync_status import SyncStatus
from app.v1.kits.domain.exceptions.repository import InvalidSyncStatusError


class TestSyncStatus:
    """Tests para el Value Object SyncStatus (never_synced | synced | sync_error)."""

    def test_sync_status_never_synced_valid(self):
        """never_synced es un estado de sincronización válido."""
        status = SyncStatus("never_synced")
        assert status.value == "never_synced"

    def test_sync_status_synced_valid(self):
        """synced es un estado de sincronización válido."""
        status = SyncStatus("synced")
        assert status.value == "synced"

    def test_sync_status_sync_error_valid(self):
        """sync_error es un estado de sincronización válido."""
        status = SyncStatus("sync_error")
        assert status.value == "sync_error"

    def test_sync_status_invalid_raises_error(self):
        """Un valor no permitido lanza InvalidSyncStatusError."""
        with pytest.raises(InvalidSyncStatusError):
            SyncStatus("pending")
