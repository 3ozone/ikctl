"""Tests para Use Case ListGroups."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest

from app.v1.servers.domain.entities.group import Group
from app.v1.servers.application.queries.list_groups import ListGroups
from app.v1.servers.application.dtos.group_list_result import GroupListResult


def make_group(group_id: str = "grp-123", user_id: str = "user-123") -> Group:
    """Factoría de Group para los tests."""
    now = datetime.now(timezone.utc)
    return Group(
        id=group_id,
        user_id=user_id,
        name="Mi grupo",
        description=None,
        server_ids=["srv-1"],
        created_at=now,
        updated_at=now,
    )


class TestListGroups:
    """Tests del Use Case ListGroups."""

    @pytest.mark.asyncio
    async def test_list_groups_returns_paginated_result(self):
        """Test 1: ListGroups devuelve GroupListResult con items y metadatos de paginación."""
        repo = AsyncMock()
        repo.find_all_by_user.return_value = [
            make_group("grp-1"), make_group("grp-2")]

        use_case = ListGroups(group_repository=repo)

        result = await use_case.execute(user_id="user-123", page=1, per_page=10)

        assert isinstance(result, GroupListResult)
        assert len(result.items) == 2
        assert result.page == 1
        assert result.per_page == 10

    @pytest.mark.asyncio
    async def test_list_groups_empty_returns_empty_list(self):
        """Test 2: ListGroups sin grupos devuelve lista vacía."""
        repo = AsyncMock()
        repo.find_all_by_user.return_value = []

        use_case = ListGroups(group_repository=repo)

        result = await use_case.execute(user_id="user-123", page=1, per_page=10)

        assert isinstance(result, GroupListResult)
        assert result.items == []
        assert result.total == 0
