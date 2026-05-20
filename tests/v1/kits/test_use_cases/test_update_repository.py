"""Tests para el Use Case UpdateRepository."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.v1.kits.application.commands.update_repository import UpdateRepository
from app.v1.kits.application.dtos.repository_result import RepositoryResult
from app.v1.kits.application.exceptions import (
    InvalidGitCredentialTypeError,
    RepositoryNotFoundError,
)
from app.v1.kits.domain.entities.repository import Repository
from app.v1.kits.domain.value_objects.sync_status import SyncStatus

CORRELATION_ID = str(uuid4())


def _make_repository(url: str = "https://github.com/org/repo.git", ref: str = "main") -> Repository:
    now = datetime.now(timezone.utc)
    return Repository(
        id="repo-123",
        user_id="user-123",
        url=url,
        ref=ref,
        credential_id=None,
        sync_status=SyncStatus("never_synced"),
        last_synced_at=None,
        last_commit_sha=None,
        sync_error_message=None,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )


class TestUpdateRepositorySuccess:
    """Tests de éxito del Use Case UpdateRepository."""

    @pytest.mark.asyncio
    async def test_update_repository_returns_repository_result(self):
        """Test 1: UpdateRepository devuelve RepositoryResult con los datos actualizados."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo

        use_case = UpdateRepository(
            repository_repository=repository_repo,
            credential_repository=AsyncMock(),
        )

        result = await use_case.execute(
            user_id="user-123",
            repository_id="repo-123",
            url="https://github.com/org/other.git",
            ref="develop",
            credential_id=None,
            correlation_id=CORRELATION_ID,
        )

        assert isinstance(result, RepositoryResult)
        assert result.url == "https://github.com/org/other.git"
        assert result.ref == "develop"

    @pytest.mark.asyncio
    async def test_update_repository_persists_via_update(self):
        """Test 2: UpdateRepository llama a repo.update() y persiste via repository_repository.update()."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo

        use_case = UpdateRepository(
            repository_repository=repository_repo,
            credential_repository=AsyncMock(),
        )

        await use_case.execute(
            user_id="user-123",
            repository_id="repo-123",
            url="https://github.com/org/other.git",
            ref="develop",
            credential_id=None,
            correlation_id=CORRELATION_ID,
        )

        repository_repo.update.assert_called_once()


class TestUpdateRepositoryError:
    """Tests de error del Use Case UpdateRepository."""

    @pytest.mark.asyncio
    async def test_update_repository_raises_error_if_not_found(self):
        """Test 3: UpdateRepository lanza RepositoryNotFoundError si el repositorio no existe (RN-01)."""
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = None

        use_case = UpdateRepository(
            repository_repository=repository_repo,
            credential_repository=AsyncMock(),
        )

        with pytest.raises(RepositoryNotFoundError):
            await use_case.execute(
                user_id="user-123",
                repository_id="repo-no-existe",
                url="https://github.com/org/repo.git",
                ref="main",
                credential_id=None,
                correlation_id=CORRELATION_ID,
            )

    @pytest.mark.asyncio
    async def test_update_repository_raises_error_if_credential_type_is_ssh(self):
        """Test 4: UpdateRepository lanza InvalidGitCredentialTypeError si la credencial es de tipo ssh (RN-23)."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo

        credential = AsyncMock()
        credential.type.value = "ssh"
        credential_repo = AsyncMock()
        credential_repo.find_by_id.return_value = credential

        use_case = UpdateRepository(
            repository_repository=repository_repo,
            credential_repository=credential_repo,
        )

        with pytest.raises(InvalidGitCredentialTypeError):
            await use_case.execute(
                user_id="user-123",
                repository_id="repo-123",
                url="https://github.com/org/repo.git",
                ref="main",
                credential_id="cred-ssh",
                correlation_id=CORRELATION_ID,
            )
