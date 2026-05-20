"""Tests para el Query ListKits."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.v1.kits.application.dtos.kit_list_result import KitListResult
from app.v1.kits.application.queries.list_kits import ListKits
from app.v1.kits.domain.entities.kit import Kit
from app.v1.kits.domain.value_objects.sync_status import SyncStatus


def _make_kit(kit_id: str = "kit-123") -> Kit:
    now = datetime.now(timezone.utc)
    return Kit(
        id=kit_id,
        user_id="user-123",
        repository_id="repo-123",
        path_in_repo=f"kits/{kit_id}",
        name=kit_id,
        description="A test kit",
        version="1.0.0",
        tags=["tag1"],
        values={"key": "value"},
        debug_level="info",
        sync_status=SyncStatus("synced"),
        last_synced_at=now,
        last_commit_sha="abc123",
        sync_error_message=None,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )


class TestListKits:
    """Tests del Query ListKits."""

    @pytest.mark.asyncio
    async def test_list_kits_returns_kit_list_result(self):
        """Test 1: ListKits devuelve KitListResult con los kits del usuario."""
        kits = [_make_kit("kit-1"), _make_kit("kit-2")]
        kit_repo = AsyncMock()
        kit_repo.find_all_by_user.return_value = kits

        use_case = ListKits(kit_repository=kit_repo)

        result = await use_case.execute(user_id="user-123", page=1, per_page=10)

        assert isinstance(result, KitListResult)
        assert len(result.items) == 2
        assert result.page == 1
        assert result.per_page == 10
        kit_repo.find_all_by_user.assert_called_once_with(
            "user-123", 1, 10, None, None
        )

    @pytest.mark.asyncio
    async def test_list_kits_returns_empty_list_when_no_kits(self):
        """Test 2: ListKits devuelve lista vacía cuando el usuario no tiene kits."""
        kit_repo = AsyncMock()
        kit_repo.find_all_by_user.return_value = []

        use_case = ListKits(kit_repository=kit_repo)

        result = await use_case.execute(user_id="user-123", page=1, per_page=10)

        assert isinstance(result, KitListResult)
        assert result.items == []
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_list_kits_passes_filters_to_repository(self):
        """Test 3: ListKits pasa tags_filter y repository_id_filter al repositorio."""
        kit_repo = AsyncMock()
        kit_repo.find_all_by_user.return_value = []

        use_case = ListKits(kit_repository=kit_repo)

        await use_case.execute(
            user_id="user-123",
            page=2,
            per_page=5,
            tags_filter=["tag1", "tag2"],
            repository_id_filter="repo-456",
        )

        kit_repo.find_all_by_user.assert_called_once_with(
            "user-123", 2, 5, ["tag1", "tag2"], "repo-456"
        )
