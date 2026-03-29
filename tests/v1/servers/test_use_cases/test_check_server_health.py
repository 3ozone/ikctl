"""Tests para Use Case CheckServerHealth."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.application.queries.check_server_health import CheckServerHealth
from app.v1.servers.application.dtos.health_check_result import HealthCheckResult


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


OS_RELEASE_OUTPUT = "ID=ubuntu\nVERSION_ID=22.04\nPRETTY_NAME=Ubuntu 22.04 LTS"


class TestCheckServerHealthSuccess:
    """Tests de éxito del Use Case CheckServerHealth."""

    @pytest.mark.asyncio
    async def test_online_server_returns_online_status_with_latency(self):
        """Test 1: Servidor accesible devuelve status online y latency_ms >= 0."""
        server_repo = AsyncMock()
        server_repo.find_by_id.return_value = make_server()

        connection = AsyncMock()
        connection.execute.return_value = (0, OS_RELEASE_OUTPUT, "")

        connection_factory = MagicMock()
        connection_factory.create = AsyncMock(return_value=connection)

        use_case = CheckServerHealth(
            server_repository=server_repo,
            connection_factory=connection_factory,
        )

        result = await use_case.execute(user_id="user-123", server_id="srv-123")

        assert isinstance(result, HealthCheckResult)
        assert result.status == "online"
        assert result.latency_ms is not None
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_online_server_parses_os_info(self):
        """Test 2: Servidor accesible parsea correctamente el SO desde /etc/os-release."""
        server_repo = AsyncMock()
        server_repo.find_by_id.return_value = make_server()

        connection = AsyncMock()
        connection.execute.return_value = (0, OS_RELEASE_OUTPUT, "")

        connection_factory = MagicMock()
        connection_factory.create = AsyncMock(return_value=connection)

        use_case = CheckServerHealth(
            server_repository=server_repo,
            connection_factory=connection_factory,
        )

        result = await use_case.execute(user_id="user-123", server_id="srv-123")

        assert result.os_id == "ubuntu"
        assert result.os_version == "22.04"
        assert result.os_name == "Ubuntu 22.04 LTS"

    @pytest.mark.asyncio
    async def test_connection_failure_returns_offline_status(self):
        """Test 3: Si la conexión falla, devuelve status offline sin lanzar excepción."""
        server_repo = AsyncMock()
        server_repo.find_by_id.return_value = make_server()

        connection_factory = MagicMock()
        connection_factory.create = AsyncMock(side_effect=ConnectionError("timeout"))

        use_case = CheckServerHealth(
            server_repository=server_repo,
            connection_factory=connection_factory,
        )

        result = await use_case.execute(user_id="user-123", server_id="srv-123")

        assert isinstance(result, HealthCheckResult)
        assert result.status == "offline"
        assert result.latency_ms is None


class TestCheckServerHealthError:
    """Tests de error del Use Case CheckServerHealth."""

    @pytest.mark.asyncio
    async def test_server_not_found_raises_error(self):
        """Test 4 (RN-01): Si el servidor no existe o no pertenece al usuario, lanza ServerNotFoundError."""
        server_repo = AsyncMock()
        server_repo.find_by_id.return_value = None

        connection_factory = MagicMock()

        use_case = CheckServerHealth(
            server_repository=server_repo,
            connection_factory=connection_factory,
        )

        with pytest.raises(ServerNotFoundError):
            await use_case.execute(user_id="user-123", server_id="srv-inexistente")
