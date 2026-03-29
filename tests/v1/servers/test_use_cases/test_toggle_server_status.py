"""Tests para Use Case ToggleServerStatus."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest

from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.application.commands.toggle_server_status import ToggleServerStatus
from app.v1.servers.application.dtos.server_result import ServerResult

CORRELATION_ID = str(uuid4())


def make_server(
    server_id: str = "srv-123",
    user_id: str = "user-123",
    status: str = "active",
) -> Server:
    """Factoría de Server para los tests."""
    now = datetime.now(timezone.utc)
    return Server(
        id=server_id,
        user_id=user_id,
        name="Mi servidor",
        type=ServerType("remote"),
        status=ServerStatus(status),
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


class TestToggleServerStatusSuccess:
    """Tests de éxito del Use Case ToggleServerStatus."""

    @pytest.mark.asyncio
    async def test_deactivate_active_server_returns_inactive_result(self):
        """Test 1: ToggleServerStatus(active=False) sobre un server activo devuelve status inactive."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_server(status="active")

        use_case = ToggleServerStatus(server_repository=repo)

        result = await use_case.execute(
            user_id="user-123",
            server_id="srv-123",
            active=False,
            correlation_id=CORRELATION_ID,
        )

        assert isinstance(result, ServerResult)
        assert result.status == "inactive"

    @pytest.mark.asyncio
    async def test_activate_inactive_server_returns_active_result(self):
        """Test 2: ToggleServerStatus(active=True) sobre un server inactivo devuelve status active."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_server(status="inactive")

        use_case = ToggleServerStatus(server_repository=repo)

        result = await use_case.execute(
            user_id="user-123",
            server_id="srv-123",
            active=True,
            correlation_id=CORRELATION_ID,
        )

        assert isinstance(result, ServerResult)
        assert result.status == "active"

    @pytest.mark.asyncio
    async def test_toggle_server_calls_repo_update(self):
        """Test 3: ToggleServerStatus llama a repo.update con el server modificado."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_server(status="active")

        use_case = ToggleServerStatus(server_repository=repo)

        await use_case.execute(
            user_id="user-123",
            server_id="srv-123",
            active=False,
            correlation_id=CORRELATION_ID,
        )

        repo.update.assert_called_once()


class TestToggleServerStatusError:
    """Tests de error del Use Case ToggleServerStatus."""

    @pytest.mark.asyncio
    async def test_toggle_server_not_found_raises_error(self):
        """Test 4 (RN-01): Si el servidor no existe o no pertenece al usuario, lanza ServerNotFoundError."""
        repo = AsyncMock()
        repo.find_by_id.return_value = None

        use_case = ToggleServerStatus(server_repository=repo)

        with pytest.raises(ServerNotFoundError):
            await use_case.execute(
                user_id="user-123",
                server_id="srv-inexistente",
                active=False,
                correlation_id=CORRELATION_ID,
            )
