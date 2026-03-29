"""Tests para Use Case UpdateServer."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest

from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.application.commands.update_server import UpdateServer
from app.v1.servers.application.dtos.server_result import ServerResult

CORRELATION_ID = str(uuid4())


def make_remote_server(server_id: str = "srv-123", user_id: str = "user-123") -> Server:
    """Factoría de Server remoto para los tests."""
    now = datetime.now(timezone.utc)
    return Server(
        id=server_id,
        user_id=user_id,
        name="Mi servidor",
        type=ServerType("remote"),
        status=ServerStatus("active"),
        host="192.168.1.1",
        port=22,
        credential_id="cred-456",
        description=None,
        os_id=None,
        os_version=None,
        os_name=None,
        created_at=now,
        updated_at=now,
    )


def make_local_server(server_id: str = "srv-local", user_id: str = "user-123") -> Server:
    """Factoría de Server local para los tests."""
    now = datetime.now(timezone.utc)
    return Server(
        id=server_id,
        user_id=user_id,
        name="Mi servidor local",
        type=ServerType("local"),
        status=ServerStatus("active"),
        host=None,
        port=None,
        credential_id=None,
        description=None,
        os_id=None,
        os_version=None,
        os_name=None,
        created_at=now,
        updated_at=now,
    )


class TestUpdateServerSuccess:
    """Tests de éxito del Use Case UpdateServer."""

    @pytest.mark.asyncio
    async def test_update_remote_server_returns_updated_result(self):
        """Test 1: UpdateServer devuelve ServerResult con los datos actualizados para un server remote."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_remote_server()
        use_case = UpdateServer(server_repository=repo)

        result = await use_case.execute(
            user_id="user-123",
            server_id="srv-123",
            name="Servidor actualizado",
            host="10.0.0.1",
            port=2222,
            credential_id="cred-789",
            description="Nueva descripción",
            correlation_id=CORRELATION_ID,
        )

        assert isinstance(result, ServerResult)
        assert result.name == "Servidor actualizado"
        assert result.host == "10.0.0.1"
        assert result.port == 2222
        assert result.credential_id == "cred-789"

    @pytest.mark.asyncio
    async def test_update_local_server_ignores_host_and_credential(self):
        """Test 2: UpdateServer en server local solo actualiza name y description, ignora host y credential_id."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_local_server()
        use_case = UpdateServer(server_repository=repo)

        result = await use_case.execute(
            user_id="user-123",
            server_id="srv-local",
            name="Local actualizado",
            host="192.168.1.99",       # debe ignorarse en local
            port=22,                   # debe ignorarse en local
            credential_id="cred-999",  # debe ignorarse en local
            description="Nueva desc",
            correlation_id=CORRELATION_ID,
        )

        assert result.name == "Local actualizado"
        assert result.description == "Nueva desc"
        assert result.host is None
        assert result.credential_id is None

    @pytest.mark.asyncio
    async def test_update_server_calls_repo_update(self):
        """Test 3: UpdateServer llama a repo.update con el servidor modificado."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_remote_server()
        use_case = UpdateServer(server_repository=repo)

        await use_case.execute(
            user_id="user-123",
            server_id="srv-123",
            name="Servidor actualizado",
            host="10.0.0.1",
            port=22,
            credential_id="cred-456",
            description=None,
            correlation_id=CORRELATION_ID,
        )

        repo.update.assert_called_once()


class TestUpdateServerError:
    """Tests de error del Use Case UpdateServer."""

    @pytest.mark.asyncio
    async def test_update_server_not_found_raises_error(self):
        """Test 4: UpdateServer lanza ServerNotFoundError si el servidor no existe o no pertenece al usuario (RN-01)."""
        repo = AsyncMock()
        repo.find_by_id.return_value = None  # no existe o no pertenece al usuario
        use_case = UpdateServer(server_repository=repo)

        with pytest.raises(ServerNotFoundError):
            await use_case.execute(
                user_id="user-123",
                server_id="srv-no-existe",
                name="Nombre",
                host="10.0.0.1",
                port=22,
                credential_id="cred-456",
                description=None,
                correlation_id=CORRELATION_ID,
            )
