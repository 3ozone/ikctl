"""Tests para Use Case RegisterLocalServer."""
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest

from app.v1.servers.application.commands.register_local_server import RegisterLocalServer
from app.v1.servers.application.dtos.server_result import ServerResult
from app.v1.servers.application.exceptions import DuplicateLocalServerError, UnauthorizedOperationError

CORRELATION_ID = str(uuid4())


class TestRegisterLocalServerSuccess:
    """Tests de éxito del Use Case RegisterLocalServer."""

    @pytest.mark.asyncio
    async def test_register_local_server_returns_server_result(self):
        """Test 1: RegisterLocalServer devuelve ServerResult de tipo local sin host ni credential_id."""
        server_repo = AsyncMock()
        # no existe servidor local previo
        server_repo.find_local_by_user.return_value = []

        use_case = RegisterLocalServer(server_repository=server_repo)

        result = await use_case.execute(
            user_id="user-123",
            user_role="admin",
            name="Mi servidor local",
            description="Servidor local de pruebas",
            correlation_id=CORRELATION_ID,
        )

        assert isinstance(result, ServerResult)
        assert result.user_id == "user-123"
        assert result.name == "Mi servidor local"
        assert result.server_type == "local"
        assert result.host is None
        assert result.credential_id is None
        assert result.server_id is not None

    @pytest.mark.asyncio
    async def test_register_local_server_calls_repo_save(self):
        """Test 2: RegisterLocalServer persiste el servidor via server_repository.save."""
        server_repo = AsyncMock()
        server_repo.find_local_by_user.return_value = []

        use_case = RegisterLocalServer(server_repository=server_repo)

        await use_case.execute(
            user_id="user-123",
            user_role="admin",
            name="Mi servidor local",
            description=None,
            correlation_id=CORRELATION_ID,
        )

        server_repo.save.assert_called_once()


class TestRegisterLocalServerError:
    """Tests de error del Use Case RegisterLocalServer."""

    @pytest.mark.asyncio
    async def test_register_local_server_duplicate_raises_error(self):
        """Test 3: RegisterLocalServer lanza DuplicateLocalServerError si ya existe un local (RN-07)."""
        server_repo = AsyncMock()
        server_repo.find_local_by_user.return_value = [
            AsyncMock()]  # ya existe un servidor local

        use_case = RegisterLocalServer(server_repository=server_repo)

        with pytest.raises(DuplicateLocalServerError):
            await use_case.execute(
                user_id="user-123",
                user_role="admin",
                name="Segundo servidor local",
                description=None,
                correlation_id=CORRELATION_ID,
            )

    @pytest.mark.asyncio
    async def test_register_local_server_non_admin_raises_error(self):
        """Test 4: RegisterLocalServer lanza UnauthorizedOperationError si el usuario no es admin (RNF-16)."""
        use_case = RegisterLocalServer(server_repository=AsyncMock())

        with pytest.raises(UnauthorizedOperationError):
            await use_case.execute(
                user_id="user-123",
                user_role="user",  # sin rol admin
                name="Mi servidor local",
                description=None,
                correlation_id=CORRELATION_ID,
            )

    @pytest.mark.asyncio
    async def test_register_local_server_non_admin_does_not_query_repo(self):
        """Test 5: RegisterLocalServer no consulta el repo si el usuario no es admin."""
        server_repo = AsyncMock()

        use_case = RegisterLocalServer(server_repository=server_repo)

        with pytest.raises(UnauthorizedOperationError):
            await use_case.execute(
                user_id="user-123",
                user_role="user",
                name="Mi servidor local",
                description=None,
                correlation_id=CORRELATION_ID,
            )

        server_repo.find_local_by_user.assert_not_called()
