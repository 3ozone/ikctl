"""Tests para el Query GetRepository."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.v1.kits.application.exceptions import RepositoryNotFoundError
from app.v1.kits.application.queries.get_repository import GetRepository
from app.v1.kits.application.dtos.repository_result import RepositoryResult
from app.v1.kits.domain.entities.repository import Repository
from app.v1.kits.domain.value_objects.sync_status import SyncStatus


def _make_repository(is_deleted: bool = False) -> Repository:
    now = datetime.now(timezone.utc)
    return Repository(
        id="repo-123",
        user_id="user-123",
        url="https://github.com/org/repo.git",
        ref="main",
        credential_id=None,
        sync_status=SyncStatus("never_synced"),
        last_synced_at=None,
        last_commit_sha=None,
        sync_error_message=None,
        is_deleted=is_deleted,
        created_at=now,
        updated_at=now,
    )


class TestGetRepositorySuccess:
    """Tests de éxito del Query GetRepository."""

    @pytest.mark.asyncio
    async def test_get_repository_returns_repository_result(self):
        """Test 1: GetRepository devuelve RepositoryResult cuando el repositorio existe."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo

        use_case = GetRepository(repository_repository=repository_repo)

        result = await use_case.execute(user_id="user-123", repository_id="repo-123")

        assert isinstance(result, RepositoryResult)
        assert result.repository_id == "repo-123"
        assert result.user_id == "user-123"


class TestGetRepositoryError:
    """Tests de error del Query GetRepository."""

    @pytest.mark.asyncio
    async def test_get_repository_raises_error_if_not_found(self):
        """Test 2: GetRepository lanza RepositoryNotFoundError si no existe o no pertenece al usuario (RN-01)."""
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = None

        use_case = GetRepository(repository_repository=repository_repo)

        with pytest.raises(RepositoryNotFoundError):
            await use_case.execute(user_id="user-123", repository_id="repo-no-existe")

    @pytest.mark.asyncio
    async def test_get_repository_raises_error_if_deleted(self):
        """Test 3: GetRepository lanza RepositoryNotFoundError si el repositorio está eliminado."""
        repo = _make_repository(is_deleted=True)
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo

        use_case = GetRepository(repository_repository=repository_repo)

        with pytest.raises(RepositoryNotFoundError):
            await use_case.execute(user_id="user-123", repository_id="repo-123")
