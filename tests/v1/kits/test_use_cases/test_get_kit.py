"""Tests para el Query GetKit."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.v1.kits.application.exceptions import KitNotFoundError
from app.v1.kits.application.queries.get_kit import GetKit
from app.v1.kits.application.dtos.kit_result import KitResult
from app.v1.kits.domain.entities.kit import Kit
from app.v1.kits.domain.value_objects.sync_status import SyncStatus


def _make_kit(is_deleted: bool = False) -> Kit:
    now = datetime.now(timezone.utc)
    return Kit(
        id="kit-123",
        user_id="user-123",
        repository_id="repo-123",
        path_in_repo="kits/my-kit",
        name="my-kit",
        description="A test kit",
        version="1.0.0",
        tags=["tag1"],
        values={"key": "value"},
        debug_level="info",
        sync_status=SyncStatus("synced"),
        last_synced_at=now,
        last_commit_sha="abc123",
        sync_error_message=None,
        is_deleted=is_deleted,
        created_at=now,
        updated_at=now,
    )


class TestGetKitSuccess:
    """Tests de éxito del Query GetKit."""

    @pytest.mark.asyncio
    async def test_get_kit_returns_kit_result(self):
        """Test 1: GetKit devuelve KitResult cuando el kit existe y no está eliminado."""
        kit = _make_kit()
        kit_repo = AsyncMock()
        kit_repo.find_by_id.return_value = kit

        use_case = GetKit(kit_repository=kit_repo)

        result = await use_case.execute(user_id="user-123", kit_id="kit-123")

        assert isinstance(result, KitResult)
        assert result.kit_id == "kit-123"
        assert result.user_id == "user-123"
        assert result.repository_id == "repo-123"
        kit_repo.find_by_id.assert_called_once_with("kit-123", "user-123")


class TestGetKitError:
    """Tests de error del Query GetKit."""

    @pytest.mark.asyncio
    async def test_get_kit_raises_error_if_not_found(self):
        """Test 2: GetKit lanza KitNotFoundError si no existe o no pertenece al usuario (RN-01)."""
        kit_repo = AsyncMock()
        kit_repo.find_by_id.return_value = None

        use_case = GetKit(kit_repository=kit_repo)

        with pytest.raises(KitNotFoundError):
            await use_case.execute(user_id="user-123", kit_id="kit-no-existe")

    @pytest.mark.asyncio
    async def test_get_kit_raises_error_if_deleted(self):
        """Test 3: GetKit lanza KitNotFoundError si el kit está eliminado (borrado suave)."""
        kit = _make_kit(is_deleted=True)
        kit_repo = AsyncMock()
        kit_repo.find_by_id.return_value = kit

        use_case = GetKit(kit_repository=kit_repo)

        with pytest.raises(KitNotFoundError):
            await use_case.execute(user_id="user-123", kit_id="kit-123")
