"""Tests para Use Case GetServer."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest

from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.application.queries.get_server import GetServer
from app.v1.servers.application.dtos.server_result import ServerResult


def make_server(server_id: str = "srv-123", user_id: str = "user-123") -> Server:
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


class TestGetServer:
    """Tests del Use Case GetServer."""

    @pytest.mark.asyncio
    async def test_get_server_returns_server_result(self):
        """Test 1: GetServer devuelve ServerResult con los datos del servidor."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_server()

        use_case = GetServer(server_repository=repo)

        result = await use_case.execute(user_id="user-123", server_id="srv-123")

        assert isinstance(result, ServerResult)
        assert result.server_id == "srv-123"
        assert result.credential_id == "cred-456"

    @pytest.mark.asyncio
    async def test_get_server_not_found_raises_error(self):
        """Test 2 (RN-01): Si el servidor no existe o no pertenece al usuario, lanza ServerNotFoundError."""
        repo = AsyncMock()
        repo.find_by_id.return_value = None

        use_case = GetServer(server_repository=repo)

        with pytest.raises(ServerNotFoundError):
            await use_case.execute(user_id="user-123", server_id="srv-inexistente")
