"""Tests para Use Case ListServers."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest

from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.application.queries.list_servers import ListServers
from app.v1.servers.application.dtos.server_list_result import ServerListResult


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


class TestListServers:
    """Tests del Use Case ListServers."""

    @pytest.mark.asyncio
    async def test_list_servers_returns_paginated_result(self):
        """Test 1: ListServers devuelve ServerListResult con items y metadatos de paginación."""
        repo = AsyncMock()
        repo.find_all_by_user.return_value = [
            make_server("srv-1"), make_server("srv-2")]

        use_case = ListServers(server_repository=repo)

        result = await use_case.execute(user_id="user-123", page=1, per_page=10)

        assert isinstance(result, ServerListResult)
        assert len(result.items) == 2
        assert result.page == 1
        assert result.per_page == 10

    @pytest.mark.asyncio
    async def test_list_servers_empty_returns_empty_list(self):
        """Test 2: ListServers sin servidores devuelve lista vacía."""
        repo = AsyncMock()
        repo.find_all_by_user.return_value = []

        use_case = ListServers(server_repository=repo)

        result = await use_case.execute(user_id="user-123", page=1, per_page=10)

        assert isinstance(result, ServerListResult)
        assert result.items == []
        assert result.total == 0
