"""Tests para el Value Object ServerType."""
import pytest

from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.exceptions.server import InvalidServerTypeError


class TestServerType:
    """Tests para el Value Object ServerType (remote | local)."""

    def test_server_type_remote_valid(self):
        """remote es un tipo de servidor válido."""
        server_type = ServerType("remote")
        assert server_type.value == "remote"

    def test_server_type_local_valid(self):
        """local es un tipo de servidor válido."""
        server_type = ServerType("local")
        assert server_type.value == "local"

    def test_server_type_invalid_raises_error(self):
        """Un tipo de servidor no permitido lanza InvalidServerTypeError."""
        with pytest.raises(InvalidServerTypeError):
            ServerType("cloud")
