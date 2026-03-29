"""Tests para Use Case DeleteServer."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest

from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.application.commands.delete_server import DeleteServer
from app.v1.servers.application.exceptions import ServerInUseError

CORRELATION_ID = str(uuid4())


def make_server(server_id: str = "srv-123", user_id: str = "user-123") -> Server:
    """Factoría de Server para los tests."""
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


class TestDeleteServerSuccess:
    """Tests de éxito del Use Case DeleteServer."""

    @pytest.mark.asyncio
    async def test_delete_server_calls_repo_delete(self):
        """Test 1: DeleteServer llama a repo.delete con el id correcto."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_server()
        repo.has_active_operations.return_value = False

        use_case = DeleteServer(server_repository=repo)

        await use_case.execute(
            user_id="user-123",
            server_id="srv-123",
            correlation_id=CORRELATION_ID,
        )

        repo.delete.assert_called_once_with("srv-123")

    @pytest.mark.asyncio
    async def test_delete_server_returns_none(self):
        """Test 2: DeleteServer devuelve None tras eliminar el servidor."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_server()
        repo.has_active_operations.return_value = False

        use_case = DeleteServer(server_repository=repo)

        result = await use_case.execute(
            user_id="user-123",
            server_id="srv-123",
            correlation_id=CORRELATION_ID,
        )

        assert result is None


class TestDeleteServerError:
    """Tests de error del Use Case DeleteServer."""

    @pytest.mark.asyncio
    async def test_delete_server_not_found_raises_error(self):
        """Test 3: DeleteServer lanza ServerNotFoundError si el servidor no existe o no pertenece al usuario (RN-01)."""
        repo = AsyncMock()
        repo.find_by_id.return_value = None

        use_case = DeleteServer(server_repository=repo)

        with pytest.raises(ServerNotFoundError):
            await use_case.execute(
                user_id="user-123",
                server_id="srv-no-existe",
                correlation_id=CORRELATION_ID,
            )

    @pytest.mark.asyncio
    async def test_delete_server_with_active_operations_raises_error(self):
        """Test 4: DeleteServer lanza ServerInUseError si el servidor tiene operaciones activas (RN-08)."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_server()
        repo.has_active_operations.return_value = True

        use_case = DeleteServer(server_repository=repo)

        with pytest.raises(ServerInUseError):
            await use_case.execute(
                user_id="user-123",
                server_id="srv-123",
                correlation_id=CORRELATION_ID,
            )
