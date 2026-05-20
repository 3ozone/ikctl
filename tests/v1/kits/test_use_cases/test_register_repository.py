"""Tests para el Use Case RegisterRepository."""
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.v1.kits.application.commands.register_repository import RegisterRepository
from app.v1.kits.application.dtos.repository_result import RepositoryResult
from app.v1.kits.application.exceptions import InvalidGitCredentialTypeError

CORRELATION_ID = str(uuid4())


class TestRegisterRepositorySuccess:
    """Tests de éxito del Use Case RegisterRepository."""

    @pytest.mark.asyncio
    async def test_register_repository_returns_repository_result(self):
        """Test 1: RegisterRepository devuelve RepositoryResult con los datos del repositorio creado."""
        credential_repo = AsyncMock()
        credential = AsyncMock()
        credential.type.value = "git_https"
        credential_repo.find_by_id.return_value = credential

        repository_repo = AsyncMock()
        event_bus = AsyncMock()

        use_case = RegisterRepository(
            repository_repository=repository_repo,
            credential_repository=credential_repo,
            event_bus=event_bus,
        )

        result = await use_case.execute(
            user_id="user-123",
            url="https://github.com/org/repo.git",
            ref="main",
            credential_id="cred-456",
            correlation_id=CORRELATION_ID,
        )

        assert isinstance(result, RepositoryResult)
        assert result.user_id == "user-123"
        assert result.url == "https://github.com/org/repo.git"
        assert result.ref == "main"
        assert result.credential_id == "cred-456"
        assert result.sync_status == "never_synced"
        assert result.repository_id is not None

    @pytest.mark.asyncio
    async def test_register_repository_persists_via_save(self):
        """Test 2: RegisterRepository persiste el repositorio via repository_repository.save."""
        credential_repo = AsyncMock()
        credential = AsyncMock()
        credential.type.value = "git_ssh"
        credential_repo.find_by_id.return_value = credential

        repository_repo = AsyncMock()
        event_bus = AsyncMock()

        use_case = RegisterRepository(
            repository_repository=repository_repo,
            credential_repository=credential_repo,
            event_bus=event_bus,
        )

        await use_case.execute(
            user_id="user-123",
            url="git@github.com:org/repo.git",
            ref="main",
            credential_id="cred-456",
            correlation_id=CORRELATION_ID,
        )

        repository_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_repository_publishes_event_after_save(self):
        """Test 3: RegisterRepository publica RepositoryRegistered después de persistir (RN-32)."""
        credential_repo = AsyncMock()
        credential = AsyncMock()
        credential.type.value = "git_https"
        credential_repo.find_by_id.return_value = credential

        repository_repo = AsyncMock()
        event_bus = AsyncMock()

        call_order = []
        repository_repo.save.side_effect = lambda _: call_order.append("save")
        event_bus.publish.side_effect = lambda _: call_order.append("publish")

        use_case = RegisterRepository(
            repository_repository=repository_repo,
            credential_repository=credential_repo,
            event_bus=event_bus,
        )

        await use_case.execute(
            user_id="user-123",
            url="https://github.com/org/repo.git",
            ref="main",
            credential_id="cred-456",
            correlation_id=CORRELATION_ID,
        )

        assert call_order == ["save", "publish"], (
            "El evento debe publicarse después de persistir, no antes (RN-32)"
        )


class TestRegisterRepositoryError:
    """Tests de error del Use Case RegisterRepository."""

    @pytest.mark.asyncio
    async def test_register_repository_raises_error_if_credential_type_is_ssh(self):
        """Test 4: RegisterRepository lanza InvalidGitCredentialTypeError si la credencial es de tipo ssh (RN-23)."""
        credential_repo = AsyncMock()
        credential = AsyncMock()
        credential.type.value = "ssh"
        credential_repo.find_by_id.return_value = credential

        use_case = RegisterRepository(
            repository_repository=AsyncMock(),
            credential_repository=credential_repo,
            event_bus=AsyncMock(),
        )

        with pytest.raises(InvalidGitCredentialTypeError):
            await use_case.execute(
                user_id="user-123",
                url="https://github.com/org/repo.git",
                ref="main",
                credential_id="cred-ssh",
                correlation_id=CORRELATION_ID,
            )
