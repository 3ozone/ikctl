"""Tests para el Use Case SyncRepository."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

import pytest

from app.v1.kits.application.commands.sync_repository import SyncRepository
from app.v1.kits.application.dtos.repository_sync_result import RepositorySyncResult
from app.v1.kits.application.exceptions import RepositoryNotFoundError
from app.v1.kits.domain.entities.kit import Kit
from app.v1.kits.domain.entities.repository import Repository
from app.v1.kits.domain.events.kit_discovered import KitDiscovered
from app.v1.kits.domain.events.repository_synced import RepositorySynced
from app.v1.kits.domain.value_objects.sync_status import SyncStatus

CORRELATION_ID = str(uuid4())

ROOT_DICT = {"kits": ["kits/mykit"]}
KIT_DICT = {"name": "mykit", "description": "My kit", "version": "1.0"}
COMMIT_SHA = "abc123def456"


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


def _make_kit(path_in_repo: str = "kits/mykit") -> Kit:
    now = datetime.now(timezone.utc)
    return Kit(
        id=str(uuid4()),
        user_id="user-123",
        repository_id="repo-123",
        path_in_repo=path_in_repo,
        name="mykit",
        description="",
        version="",
        tags=[],
        values={},
        debug_level="none",
        sync_status=SyncStatus("synced"),
        last_synced_at=now,
        last_commit_sha=COMMIT_SHA,
        sync_error_message=None,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )


def _make_use_case(
    repository_repo=None,
    kit_repo=None,
    git_client=None,
    event_bus=None,
) -> SyncRepository:
    return SyncRepository(
        repository_repository=repository_repo or AsyncMock(),
        kit_repository=kit_repo or AsyncMock(),
        git_client=git_client or AsyncMock(),
        event_bus=event_bus or AsyncMock(),
    )


class TestSyncRepositorySuccess:
    """Tests de éxito del Use Case SyncRepository."""

    @pytest.mark.asyncio
    async def test_sync_returns_synced_result_on_success(self):
        """Test 1: SyncRepository devuelve RepositorySyncResult con sync_status=synced."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo

        kit_repo = AsyncMock()
        kit_repo.find_by_repository_id.return_value = []

        git_client = AsyncMock()
        git_client.clone_shallow.return_value = COMMIT_SHA
        git_client.read_yaml_file.side_effect = [ROOT_DICT, KIT_DICT]

        use_case = _make_use_case(
            repository_repo=repository_repo,
            kit_repo=kit_repo,
            git_client=git_client,
        )

        result = await use_case.execute(
            user_id="user-123",
            repository_id="repo-123",
            correlation_id=CORRELATION_ID,
        )

        assert isinstance(result, RepositorySyncResult)
        assert result.sync_status == "synced"
        assert result.last_commit_sha == COMMIT_SHA

    @pytest.mark.asyncio
    async def test_sync_creates_new_kit_when_path_is_new(self):
        """Test 2: SyncRepository crea un kit nuevo cuando el path no existe en DB (kits_created=1)."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo

        kit_repo = AsyncMock()
        kit_repo.find_by_repository_id.return_value = []  # ningún kit en DB

        git_client = AsyncMock()
        git_client.clone_shallow.return_value = COMMIT_SHA
        git_client.read_yaml_file.side_effect = [ROOT_DICT, KIT_DICT]

        use_case = _make_use_case(
            repository_repo=repository_repo,
            kit_repo=kit_repo,
            git_client=git_client,
        )

        result = await use_case.execute(
            user_id="user-123",
            repository_id="repo-123",
            correlation_id=CORRELATION_ID,
        )

        assert result.kits_created == 1
        assert result.kits_updated == 0
        kit_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_updates_existing_kit(self):
        """Test 3: SyncRepository actualiza un kit existente cuando el path ya está en DB (kits_updated=1)."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo

        existing_kit = _make_kit("kits/mykit")
        kit_repo = AsyncMock()
        kit_repo.find_by_repository_id.return_value = [existing_kit]

        git_client = AsyncMock()
        git_client.clone_shallow.return_value = COMMIT_SHA
        git_client.read_yaml_file.side_effect = [ROOT_DICT, KIT_DICT]

        use_case = _make_use_case(
            repository_repo=repository_repo,
            kit_repo=kit_repo,
            git_client=git_client,
        )

        result = await use_case.execute(
            user_id="user-123",
            repository_id="repo-123",
            correlation_id=CORRELATION_ID,
        )

        assert result.kits_updated == 1
        assert result.kits_created == 0
        kit_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_soft_deletes_kit_when_path_removed_from_index(self):
        """Test 4: SyncRepository hace soft_delete del kit cuyo path ya no está en el índice (kits_deleted=1)."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo

        # DB tiene "kits/old", índice solo tiene "kits/mykit"
        old_kit = _make_kit("kits/old")
        existing_kit = _make_kit("kits/mykit")
        kit_repo = AsyncMock()
        kit_repo.find_by_repository_id.return_value = [old_kit, existing_kit]

        # índice tiene solo kits/mykit, kits/old desaparece
        root_dict_two = {"kits": ["kits/mykit"]}
        git_client = AsyncMock()
        git_client.clone_shallow.return_value = COMMIT_SHA
        git_client.read_yaml_file.side_effect = [root_dict_two, KIT_DICT]

        use_case = _make_use_case(
            repository_repo=repository_repo,
            kit_repo=kit_repo,
            git_client=git_client,
        )

        result = await use_case.execute(
            user_id="user-123",
            repository_id="repo-123",
            correlation_id=CORRELATION_ID,
        )

        assert result.kits_deleted == 1
        assert old_kit.is_deleted is True

    @pytest.mark.asyncio
    async def test_sync_publishes_repository_synced_event_after_persist(self):
        """Test 5: SyncRepository publica RepositorySynced después de persistir (RN-32)."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo

        kit_repo = AsyncMock()
        kit_repo.find_by_repository_id.return_value = []

        git_client = AsyncMock()
        git_client.clone_shallow.return_value = COMMIT_SHA
        git_client.read_yaml_file.side_effect = [ROOT_DICT, KIT_DICT]

        event_bus = AsyncMock()
        call_order = []
        kit_repo.save.side_effect = lambda _: call_order.append("kit_save")
        repository_repo.update.side_effect = lambda _: call_order.append("repo_update")
        event_bus.publish.side_effect = lambda _: call_order.append("publish")

        use_case = _make_use_case(
            repository_repo=repository_repo,
            kit_repo=kit_repo,
            git_client=git_client,
            event_bus=event_bus,
        )

        await use_case.execute(
            user_id="user-123",
            repository_id="repo-123",
            correlation_id=CORRELATION_ID,
        )

        publish_index = next(i for i, v in enumerate(call_order) if v == "publish")
        persist_indices = [i for i, v in enumerate(call_order) if v in ("kit_save", "repo_update")]
        assert all(p < publish_index for p in persist_indices), (
            "Los eventos deben publicarse después de persistir (RN-32)"
        )

    @pytest.mark.asyncio
    async def test_sync_publishes_kit_discovered_for_new_kit(self):
        """Test 6: SyncRepository publica KitDiscovered por cada kit nuevo descubierto (RN-33)."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo

        kit_repo = AsyncMock()
        kit_repo.find_by_repository_id.return_value = []

        git_client = AsyncMock()
        git_client.clone_shallow.return_value = COMMIT_SHA
        git_client.read_yaml_file.side_effect = [ROOT_DICT, KIT_DICT]

        event_bus = AsyncMock()

        use_case = _make_use_case(
            repository_repo=repository_repo,
            kit_repo=kit_repo,
            git_client=git_client,
            event_bus=event_bus,
        )

        await use_case.execute(
            user_id="user-123",
            repository_id="repo-123",
            correlation_id=CORRELATION_ID,
        )

        published_types = [
            type(c.args[0]).__name__ for c in event_bus.publish.call_args_list
        ]
        assert "KitDiscovered" in published_types


class TestSyncRepositoryError:
    """Tests de error del Use Case SyncRepository."""

    @pytest.mark.asyncio
    async def test_sync_marks_sync_error_when_no_root_manifest(self):
        """Test 7: SyncRepository marca sync_error cuando no existe ikctl.yaml raíz — devuelve 200, no 500."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo

        git_client = AsyncMock()
        git_client.clone_shallow.return_value = COMMIT_SHA
        git_client.read_yaml_file.side_effect = Exception("ikctl.yaml not found")

        use_case = _make_use_case(
            repository_repo=repository_repo,
            git_client=git_client,
        )

        result = await use_case.execute(
            user_id="user-123",
            repository_id="repo-123",
            correlation_id=CORRELATION_ID,
        )

        assert result.sync_status == "sync_error"
        assert result.sync_error_message is not None

    @pytest.mark.asyncio
    async def test_sync_does_not_publish_events_on_sync_error(self):
        """Test 8: SyncRepository no publica ningún evento si el sync falla (RN-33)."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo

        git_client = AsyncMock()
        git_client.clone_shallow.return_value = COMMIT_SHA
        git_client.read_yaml_file.side_effect = Exception("ikctl.yaml not found")

        event_bus = AsyncMock()

        use_case = _make_use_case(
            repository_repo=repository_repo,
            git_client=git_client,
            event_bus=event_bus,
        )

        await use_case.execute(
            user_id="user-123",
            repository_id="repo-123",
            correlation_id=CORRELATION_ID,
        )

        event_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_raises_error_if_repository_not_found(self):
        """Test 9: SyncRepository lanza RepositoryNotFoundError si el repositorio no existe (RN-01)."""
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = None

        use_case = _make_use_case(repository_repo=repository_repo)

        with pytest.raises(RepositoryNotFoundError):
            await use_case.execute(
                user_id="user-123",
                repository_id="repo-no-existe",
                correlation_id=CORRELATION_ID,
            )

    @pytest.mark.asyncio
    async def test_sync_persists_sync_error_when_clone_fails(self):
        """Test 10: SyncRepository persiste el sync_error via repository_repo.update cuando el clone falla."""
        repo = _make_repository()
        repository_repo = AsyncMock()
        repository_repo.find_by_id.return_value = repo

        git_client = AsyncMock()
        git_client.clone_shallow.side_effect = Exception("Connection refused")

        use_case = _make_use_case(
            repository_repo=repository_repo,
            git_client=git_client,
        )

        await use_case.execute(
            user_id="user-123",
            repository_id="repo-123",
            correlation_id=CORRELATION_ID,
        )

        repository_repo.update.assert_called_once()
        assert repo.sync_status == SyncStatus("sync_error")
