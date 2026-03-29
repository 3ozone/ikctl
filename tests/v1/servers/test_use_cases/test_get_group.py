"""Tests para Use Case GetGroup."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest

from app.v1.servers.domain.entities.group import Group
from app.v1.servers.domain.exceptions.group import GroupNotFoundError
from app.v1.servers.application.queries.get_group import GetGroup
from app.v1.servers.application.dtos.group_result import GroupResult


def make_group(group_id: str = "grp-123", user_id: str = "user-123") -> Group:
    now = datetime.now(timezone.utc)
    return Group(
        id=group_id,
        user_id=user_id,
        name="Mi grupo",
        description="Descripción",
        server_ids=["srv-1", "srv-2"],
        created_at=now,
        updated_at=now,
    )


class TestGetGroup:
    """Tests del Use Case GetGroup."""

    @pytest.mark.asyncio
    async def test_get_group_returns_group_result_with_server_ids(self):
        """Test 1: GetGroup devuelve GroupResult con la lista de server_ids."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_group()

        use_case = GetGroup(group_repository=repo)

        result = await use_case.execute(user_id="user-123", group_id="grp-123")

        assert isinstance(result, GroupResult)
        assert result.group_id == "grp-123"
        assert result.server_ids == ["srv-1", "srv-2"]

    @pytest.mark.asyncio
    async def test_get_group_not_found_raises_error(self):
        """Test 2 (RN-01): Si el grupo no existe o no pertenece al usuario, lanza GroupNotFoundError."""
        repo = AsyncMock()
        repo.find_by_id.return_value = None

        use_case = GetGroup(group_repository=repo)

        with pytest.raises(GroupNotFoundError):
            await use_case.execute(user_id="user-123", group_id="grp-inexistente")
