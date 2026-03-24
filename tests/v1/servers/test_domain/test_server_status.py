"""Tests para el Value Object ServerStatus."""
import pytest

from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.exceptions.server import InvalidServerStatusError


class TestServerStatus:
    """Tests para el Value Object ServerStatus (active | inactive)."""

    def test_server_status_active_valid(self):
        """active es un estado de servidor válido."""
        status = ServerStatus("active")
        assert status.value == "active"

    def test_server_status_inactive_valid(self):
        """inactive es un estado de servidor válido."""
        status = ServerStatus("inactive")
        assert status.value == "inactive"

    def test_server_status_invalid_raises_error(self):
        """Un estado no permitido lanza InvalidServerStatusError."""
        with pytest.raises(InvalidServerStatusError):
            ServerStatus("pending")
