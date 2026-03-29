"""Tests para Use Case ExecuteAdHocCommand."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.application.queries.execute_ad_hoc_command import ExecuteAdHocCommand
from app.v1.servers.application.dtos.ad_hoc_command_result import AdHocCommandResult


def make_server(server_id: str = "srv-123", user_id: str = "user-123", status: str = "active") -> Server:
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


class TestExecuteAdHocCommandSuccess:
    """Tests de éxito del Use Case ExecuteAdHocCommand."""

    @pytest.mark.asyncio
    async def test_execute_command_returns_result(self):
        """Test 1: ExecuteAdHocCommand devuelve AdHocCommandResult con stdout, stderr y exit_code."""
        server_repo = AsyncMock()
        server_repo.find_by_id.return_value = make_server()

        connection = AsyncMock()
        connection.execute.return_value = (0, "hello world", "")

        connection_factory = MagicMock()
        connection_factory.create = AsyncMock(return_value=connection)

        use_case = ExecuteAdHocCommand(
            server_repository=server_repo,
            connection_factory=connection_factory,
        )

        result = await use_case.execute(
            user_id="user-123",
            server_id="srv-123",
            command="echo hello world",
        )

        assert isinstance(result, AdHocCommandResult)
        assert result.stdout == "hello world"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.command == "echo hello world"

    @pytest.mark.asyncio
    async def test_execute_command_with_nonzero_exit_code(self):
        """Test 2: ExecuteAdHocCommand devuelve el exit_code no cero sin lanzar excepción."""
        server_repo = AsyncMock()
        server_repo.find_by_id.return_value = make_server()

        connection = AsyncMock()
        connection.execute.return_value = (1, "", "command not found")

        connection_factory = MagicMock()
        connection_factory.create = AsyncMock(return_value=connection)

        use_case = ExecuteAdHocCommand(
            server_repository=server_repo,
            connection_factory=connection_factory,
        )

        result = await use_case.execute(
            user_id="user-123",
            server_id="srv-123",
            command="invalid_cmd",
        )

        assert result.exit_code == 1
        assert result.stderr == "command not found"


class TestExecuteAdHocCommandError:
    """Tests de error del Use Case ExecuteAdHocCommand."""

    @pytest.mark.asyncio
    async def test_server_not_found_raises_error(self):
        """Test 3 (RN-01): Si el servidor no existe o no pertenece al usuario, lanza ServerNotFoundError."""
        server_repo = AsyncMock()
        server_repo.find_by_id.return_value = None

        connection_factory = MagicMock()

        use_case = ExecuteAdHocCommand(
            server_repository=server_repo,
            connection_factory=connection_factory,
        )

        with pytest.raises(ServerNotFoundError):
            await use_case.execute(
                user_id="user-123",
                server_id="srv-inexistente",
                command="ls",
            )
