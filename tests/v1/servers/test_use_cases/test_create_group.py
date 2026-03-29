"""Tests para Use Case CreateGroup."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest

from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.application.commands.create_group import CreateGroup
from app.v1.servers.application.dtos.group_result import GroupResult
from app.v1.servers.application.exceptions import LocalServerNotAllowedInGroupError

CORRELATION_ID = str(uuid4())


def make_remote_server(server_id: str = "srv-remote", user_id: str = "user-123") -> Server:
    """Factoría de Server remoto para los tests."""
    now = datetime.now(timezone.utc)
    return Server(
        id=server_id,
        user_id=user_id,
        name="Servidor remoto",
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
        name="Servidor local",
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


class TestCreateGroupSuccess:
    """Tests de éxito del Use Case CreateGroup."""

    @pytest.mark.asyncio
    async def test_create_group_returns_group_result(self):
        """Test 1: CreateGroup con server_ids válidos devuelve GroupResult."""
        group_repo = AsyncMock()
        server_repo = AsyncMock()
        server_repo.find_by_id.return_value = make_remote_server()

        use_case = CreateGroup(group_repository=group_repo,
                               server_repository=server_repo)

        result = await use_case.execute(
            user_id="user-123",
            name="Mi grupo",
            description="Descripción del grupo",
            server_ids=["srv-remote"],
            correlation_id=CORRELATION_ID,
        )

        assert isinstance(result, GroupResult)
        assert result.name == "Mi grupo"
        assert result.server_ids == ["srv-remote"]

    @pytest.mark.asyncio
    async def test_create_group_calls_repo_save(self):
        """Test 2: CreateGroup llama a repo.save con la entidad Group."""
        group_repo = AsyncMock()
        server_repo = AsyncMock()
        server_repo.find_by_id.return_value = make_remote_server()

        use_case = CreateGroup(group_repository=group_repo,
                               server_repository=server_repo)

        await use_case.execute(
            user_id="user-123",
            name="Mi grupo",
            description=None,
            server_ids=["srv-remote"],
            correlation_id=CORRELATION_ID,
        )

        group_repo.save.assert_called_once()


class TestCreateGroupError:
    """Tests de error del Use Case CreateGroup."""

    @pytest.mark.asyncio
    async def test_create_group_with_unknown_server_raises_error(self):
        """Test 3 (RN-01): Si un server_id no existe o no pertenece al usuario, lanza ServerNotFoundError."""
        group_repo = AsyncMock()
        server_repo = AsyncMock()
        server_repo.find_by_id.return_value = None

        use_case = CreateGroup(group_repository=group_repo,
                               server_repository=server_repo)

        with pytest.raises(ServerNotFoundError):
            await use_case.execute(
                user_id="user-123",
                name="Mi grupo",
                description=None,
                server_ids=["srv-inexistente"],
                correlation_id=CORRELATION_ID,
            )

    @pytest.mark.asyncio
    async def test_create_group_with_local_server_raises_error(self):
        """Test 4 (RNF-16): Si un server_id es de tipo local, lanza LocalServerNotAllowedInGroupError."""
        group_repo = AsyncMock()
        server_repo = AsyncMock()
        server_repo.find_by_id.return_value = make_local_server()

        use_case = CreateGroup(group_repository=group_repo,
                               server_repository=server_repo)

        with pytest.raises(LocalServerNotAllowedInGroupError):
            await use_case.execute(
                user_id="user-123",
                name="Mi grupo",
                description=None,
                server_ids=["srv-local"],
                correlation_id=CORRELATION_ID,
            )
