"""Tests para el Use Case DeleteRepository."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.v1.kits.application.commands.delete_repository import DeleteRepository
from app.v1.kits.application.exceptions import (
    RepositoryInUseError,
    RepositoryNotFoundError,
)
from app.v1.kits.domain.entities.repository import Repository
from app.v1.kits.domain.value_objects.sync_status import SyncStatus

CORRELATION_ID = str(uuid4())


def _make_repository() -> Repository:
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
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )


class TestDeleteRepositorySuccess:
    """Tests de éxito del Use Case DeleteRepository."""

    @pytest.mark.asyncio
    async def test_delete_repository_calls_repo_delete(self):
        """Test 1: DeleteRepository llama a repository_repository.delete cuando no hay referencias."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo
        repository_repo.has_kits_with_references.return_value = False
        event_bus = AsyncMock()

        use_case = DeleteRepository(
            repository_repository=repository_repo,
            event_bus=event_bus,
        )

        await use_case.execute(
            user_id="user-123",
            repository_id="repo-123",
            correlation_id=CORRELATION_ID,
        )

        repository_repo.delete.assert_called_once_with("repo-123")

    @pytest.mark.asyncio
    async def test_delete_repository_publishes_event_after_delete(self):
        """Test 2: DeleteRepository publica RepositoryDeleted después de eliminar (RN-32)."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo
        repository_repo.has_kits_with_references.return_value = False
        event_bus = AsyncMock()

        call_order = []
        repository_repo.delete.side_effect = lambda _: call_order.append("delete")
        event_bus.publish.side_effect = lambda _: call_order.append("publish")

        use_case = DeleteRepository(
            repository_repository=repository_repo,
            event_bus=event_bus,
        )

        await use_case.execute(
            user_id="user-123",
            repository_id="repo-123",
            correlation_id=CORRELATION_ID,
        )

        assert call_order == ["delete", "publish"], (
            "El evento debe publicarse después de eliminar, no antes (RN-32)"
        )


class TestDeleteRepositoryError:
    """Tests de error del Use Case DeleteRepository."""

    @pytest.mark.asyncio
    async def test_delete_repository_raises_error_if_not_found(self):
        """Test 3: DeleteRepository lanza RepositoryNotFoundError si el repositorio no existe (RN-01)."""
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = None

        use_case = DeleteRepository(
            repository_repository=repository_repo,
            event_bus=AsyncMock(),
        )

        with pytest.raises(RepositoryNotFoundError):
            await use_case.execute(
                user_id="user-123",
                repository_id="repo-no-existe",
                correlation_id=CORRELATION_ID,
            )

    @pytest.mark.asyncio
    async def test_delete_repository_raises_error_if_kits_have_references(self):
        """Test 4: DeleteRepository lanza RepositoryInUseError si sus kits tienen referencias activas (RN-30)."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo
        repository_repo.has_kits_with_references.return_value = True

        use_case = DeleteRepository(
            repository_repository=repository_repo,
            event_bus=AsyncMock(),
        )

        with pytest.raises(RepositoryInUseError):
            await use_case.execute(
                user_id="user-123",
                repository_id="repo-123",
                correlation_id=CORRELATION_ID,
            )

    @pytest.mark.asyncio
    async def test_delete_repository_does_not_delete_if_references_exist(self):
        """Test 5: DeleteRepository no llama a delete si hay referencias activas (sin estado parcial)."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo
        repository_repo.has_kits_with_references.return_value = True

        use_case = DeleteRepository(
            repository_repository=repository_repo,
            event_bus=AsyncMock(),
        )

        with pytest.raises(RepositoryInUseError):
            await use_case.execute(
                user_id="user-123",
                repository_id="repo-123",
                correlation_id=CORRELATION_ID,
            )

        repository_repo.delete.assert_not_called()
