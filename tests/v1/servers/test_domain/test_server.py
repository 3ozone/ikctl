"""Tests para la entity Server."""
from datetime import datetime

import pytest

from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.exceptions.server import InvalidServerConfigurationError


CREATED_AT = datetime(2026, 1, 1, 12, 0, 0)
UPDATED_AT = datetime(2026, 1, 1, 12, 0, 0)


class TestServerRemote:
    """Tests para servidores de tipo remote."""

    def test_remote_valid(self):
        """remote con host y credential_id es válido."""
        server = Server(
            id="srv-1",
            user_id="user-1",
            name="Producción",
            type=ServerType("remote"),
            status=ServerStatus("active"),
            host="192.168.1.10",
            port=22,
            credential_id="cred-1",
            description="Servidor de producción",
            os_id=None,
            os_version=None,
            os_name=None,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        assert server.host == "192.168.1.10"
        assert server.credential_id == "cred-1"

    def test_remote_without_host_raises_error(self):
        """remote sin host lanza InvalidServerConfigurationError."""
        with pytest.raises(InvalidServerConfigurationError):
            Server(
                id="srv-2",
                user_id="user-1",
                name="Sin host",
                type=ServerType("remote"),
                status=ServerStatus("active"),
                host=None,
                port=22,
                credential_id="cred-1",
                description=None,
                os_id=None,
                os_version=None,
                os_name=None,
                created_at=CREATED_AT,
                updated_at=UPDATED_AT,
            )

    def test_remote_without_credential_id_is_valid(self):
        """remote sin credential_id es válido — la credencial es opcional al registrar."""
        server = Server(
            id="srv-3",
            user_id="user-1",
            name="Sin credencial",
            type=ServerType("remote"),
            status=ServerStatus("active"),
            host="192.168.1.10",
            port=22,
            credential_id=None,
            description=None,
            os_id=None,
            os_version=None,
            os_name=None,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        assert server.credential_id is None


class TestServerLocal:
    """Tests para servidores de tipo local."""

    def test_local_valid(self):
        """local sin host ni credential_id es válido."""
        server = Server(
            id="srv-4",
            user_id="user-1",
            name="Local",
            type=ServerType("local"),
            status=ServerStatus("active"),
            host=None,
            port=None,
            credential_id=None,
            description=None,
            os_id=None,
            os_version=None,
            os_name=None,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        assert server.host is None
        assert server.credential_id is None

    def test_local_with_host_raises_error(self):
        """local con host lanza InvalidServerConfigurationError."""
        with pytest.raises(InvalidServerConfigurationError):
            Server(
                id="srv-5",
                user_id="user-1",
                name="Local con host",
                type=ServerType("local"),
                status=ServerStatus("active"),
                host="localhost",
                port=None,
                credential_id=None,
                description=None,
                os_id=None,
                os_version=None,
                os_name=None,
                created_at=CREATED_AT,
                updated_at=UPDATED_AT,
            )


class TestServerCommands:
    """Tests para los comandos de negocio de la entity Server."""

    def _make_remote_server(self, server_id: str = "srv-6") -> Server:
        return Server(
            id=server_id,
            user_id="user-1",
            name="Servidor",
            type=ServerType("remote"),
            status=ServerStatus("active"),
            host="10.0.0.1",
            port=22,
            credential_id="cred-1",
            description=None,
            os_id=None,
            os_version=None,
            os_name=None,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )

    def test_deactivate_sets_status_inactive(self):
        """deactivate() cambia el status a inactive."""
        server = self._make_remote_server()
        server.deactivate()
        assert server.status == ServerStatus("inactive")

    def test_activate_sets_status_active(self):
        """activate() cambia el status a active."""
        server = self._make_remote_server()
        server.deactivate()
        server.activate()
        assert server.status == ServerStatus("active")

    def test_update_os_info_stores_os_fields(self):
        """update_os_info() actualiza os_id, os_version y os_name."""
        server = self._make_remote_server()
        server.update_os_info(
            os_id="ubuntu", os_version="22.04", os_name="Ubuntu 22.04 LTS")
        assert server.os_id == "ubuntu"
        assert server.os_version == "22.04"
        assert server.os_name == "Ubuntu 22.04 LTS"


class TestServerQueries:
    """Tests para las queries de la entity Server."""

    def test_is_active_returns_true_when_active(self):
        """is_active() devuelve True cuando el status es active."""
        server = Server(
            id="srv-7",
            user_id="user-1",
            name="Activo",
            type=ServerType("remote"),
            status=ServerStatus("active"),
            host="10.0.0.1",
            port=22,
            credential_id="cred-1",
            description=None,
            os_id=None,
            os_version=None,
            os_name=None,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        assert server.is_active() is True

    def test_is_local_and_is_remote(self):
        """is_local() y is_remote() devuelven el valor correcto según el tipo."""
        local = Server(
            id="srv-8",
            user_id="user-1",
            name="Local",
            type=ServerType("local"),
            status=ServerStatus("active"),
            host=None,
            port=None,
            credential_id=None,
            description=None,
            os_id=None,
            os_version=None,
            os_name=None,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        assert local.is_local() is True
        assert local.is_remote() is False


class TestServerEquality:
    """Tests para la igualdad por identidad de la entity Server."""

    def test_eq_by_id(self):
        """Dos Server con el mismo id son iguales aunque difieran en campos."""
        server_a = Server(
            id="srv-9",
            user_id="user-1",
            name="A",
            type=ServerType("remote"),
            status=ServerStatus("active"),
            host="10.0.0.1",
            port=22,
            credential_id="cred-1",
            description=None,
            os_id=None,
            os_version=None,
            os_name=None,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        server_b = Server(
            id="srv-9",
            user_id="user-2",
            name="B",
            type=ServerType("local"),
            status=ServerStatus("inactive"),
            host=None,
            port=None,
            credential_id=None,
            description=None,
            os_id=None,
            os_version=None,
            os_name=None,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        assert server_a == server_b
