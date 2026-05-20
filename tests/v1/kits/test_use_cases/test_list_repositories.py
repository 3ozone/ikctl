"""Tests para el Query ListRepositories."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.v1.kits.application.dtos.repository_list_result import RepositoryListResult
from app.v1.kits.application.queries.list_repositories import ListRepositories
from app.v1.kits.domain.entities.repository import Repository
from app.v1.kits.domain.value_objects.sync_status import SyncStatus


def _make_repository(repo_id: str = "repo-123") -> Repository:
    now = datetime.now(timezone.utc)
    return Repository(
        id=repo_id,
        user_id="user-123",
        url="https://github.com/org/repo.git",
        ref="main",
        credential_id=None,
        sync_status=SyncStatus("never_synced"),
        last_synced_at=None,
        last_commit_sha=None,
        sync_error_message=None,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )


class TestListRepositories:
    """Tests del Query ListRepositories."""

    @pytest.mark.asyncio
    async def test_list_repositories_returns_repository_list_result(self):
        """Test 1: ListRepositories devuelve RepositoryListResult con los repositorios del usuario."""
        repos = [_make_repository("repo-1"), _make_repository("repo-2")]
        repository_repo = AsyncMock()
        repository_repo.find_all_by_user.return_value = repos

        use_case = ListRepositories(repository_repository=repository_repo)

        result = await use_case.execute(user_id="user-123", page=1, per_page=10)

        assert isinstance(result, RepositoryListResult)
        assert len(result.items) == 2
        assert result.page == 1
        assert result.per_page == 10
        repository_repo.find_all_by_user.assert_called_once_with("user-123", 1, 10)

    @pytest.mark.asyncio
    async def test_list_repositories_returns_empty_list_when_no_repositories(self):
        """Test 2: ListRepositories devuelve lista vacía cuando el usuario no tiene repositorios."""
        repository_repo = AsyncMock()
        repository_repo.find_all_by_user.return_value = []

        use_case = ListRepositories(repository_repository=repository_repo)

        result = await use_case.execute(user_id="user-123", page=1, per_page=10)

        assert isinstance(result, RepositoryListResult)
        assert result.items == []
        assert result.total == 0
