"""Tests para Use Case RegisterServer."""
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest

from app.v1.servers.application.commands.register_server import RegisterServer
from app.v1.servers.application.dtos.server_result import ServerResult
from app.v1.servers.domain.exceptions.credential import CredentialNotFoundError

CORRELATION_ID = str(uuid4())


class TestRegisterServerSuccess:
    """Tests de éxito del Use Case RegisterServer."""

    @pytest.mark.asyncio
    async def test_register_server_returns_server_result(self):
        """Test 1: RegisterServer devuelve ServerResult con los datos del servidor creado."""
        credential_repo = AsyncMock()
        credential_repo.find_by_id.return_value = AsyncMock()  # credencial existe

        server_repo = AsyncMock()

        use_case = RegisterServer(
            server_repository=server_repo,
            credential_repository=credential_repo,
        )

        result = await use_case.execute(
            user_id="user-123",
            name="Mi servidor",
            host="192.168.1.1",
            port=22,
            credential_id="cred-456",
            description="Servidor de producción",
            correlation_id=CORRELATION_ID,
        )

        assert isinstance(result, ServerResult)
        assert result.user_id == "user-123"
        assert result.name == "Mi servidor"
        assert result.host == "192.168.1.1"
        assert result.port == 22
        assert result.credential_id == "cred-456"
        assert result.server_type == "remote"
        assert result.server_id is not None

    @pytest.mark.asyncio
    async def test_register_server_calls_repo_save(self):
        """Test 2: RegisterServer persiste el servidor via server_repository.save."""
        credential_repo = AsyncMock()
        credential_repo.find_by_id.return_value = AsyncMock()  # credencial existe

        server_repo = AsyncMock()

        use_case = RegisterServer(
            server_repository=server_repo,
            credential_repository=credential_repo,
        )

        await use_case.execute(
            user_id="user-123",
            name="Mi servidor",
            host="192.168.1.1",
            port=22,
            credential_id="cred-456",
            description=None,
            correlation_id=CORRELATION_ID,
        )

        server_repo.save.assert_called_once()


class TestRegisterServerError:
    """Tests de error del Use Case RegisterServer."""

    @pytest.mark.asyncio
    async def test_register_server_credential_not_found_raises_error(self):
        """Test 3: RegisterServer lanza CredentialNotFoundError si la credencial no existe."""
        credential_repo = AsyncMock()
        credential_repo.find_by_id.return_value = None  # credencial no existe

        use_case = RegisterServer(
            server_repository=AsyncMock(),
            credential_repository=credential_repo,
        )

        with pytest.raises(CredentialNotFoundError):
            await use_case.execute(
                user_id="user-123",
                name="Mi servidor",
                host="192.168.1.1",
                port=22,
                credential_id="cred-no-existe",
                description=None,
                correlation_id=CORRELATION_ID,
            )
