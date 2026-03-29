"""Tests para Use Case UpdateGroup."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest

from app.v1.servers.domain.entities.group import Group
from app.v1.servers.domain.exceptions.group import GroupNotFoundError
from app.v1.servers.application.commands.update_group import UpdateGroup
from app.v1.servers.application.dtos.group_result import GroupResult

CORRELATION_ID = str(uuid4())


def make_group(group_id: str = "grp-123", user_id: str = "user-123") -> Group:
    """Factoría de Group para los tests."""
    now = datetime.now(timezone.utc)
    return Group(
        id=group_id,
        user_id=user_id,
        name="Mi grupo",
        description="Descripción original",
        server_ids=["srv-1", "srv-2"],
        created_at=now,
        updated_at=now,
    )


class TestUpdateGroupSuccess:
    """Tests de éxito del Use Case UpdateGroup."""

    @pytest.mark.asyncio
    async def test_update_group_returns_updated_result(self):
        """Test 1: UpdateGroup devuelve GroupResult con los datos actualizados."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_group()

        use_case = UpdateGroup(group_repository=repo)

        result = await use_case.execute(
            user_id="user-123",
            group_id="grp-123",
            name="Grupo actualizado",
            description="Nueva descripción",
            server_ids=["srv-3"],
            correlation_id=CORRELATION_ID,
        )

        assert isinstance(result, GroupResult)
        assert result.name == "Grupo actualizado"
        assert result.description == "Nueva descripción"
        assert result.server_ids == ["srv-3"]

    @pytest.mark.asyncio
    async def test_update_group_calls_repo_update(self):
        """Test 2: UpdateGroup llama a repo.update con el grupo modificado."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_group()

        use_case = UpdateGroup(group_repository=repo)

        await use_case.execute(
            user_id="user-123",
            group_id="grp-123",
            name="Grupo actualizado",
            description=None,
            server_ids=["srv-1"],
            correlation_id=CORRELATION_ID,
        )

        repo.update.assert_called_once()


class TestUpdateGroupError:
    """Tests de error del Use Case UpdateGroup."""

    @pytest.mark.asyncio
    async def test_update_group_not_found_raises_error(self):
        """Test 3 (RN-01): Si el grupo no existe o no pertenece al usuario, lanza GroupNotFoundError."""
        repo = AsyncMock()
        repo.find_by_id.return_value = None

        use_case = UpdateGroup(group_repository=repo)

        with pytest.raises(GroupNotFoundError):
            await use_case.execute(
                user_id="user-123",
                group_id="grp-inexistente",
                name="Nuevo nombre",
                description=None,
                server_ids=[],
                correlation_id=CORRELATION_ID,
            )
