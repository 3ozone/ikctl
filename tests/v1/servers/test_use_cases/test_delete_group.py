"""Tests para Use Case DeleteGroup."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest

from app.v1.servers.domain.entities.group import Group
from app.v1.servers.domain.exceptions.group import GroupNotFoundError
from app.v1.servers.application.commands.delete_group import DeleteGroup
from app.v1.servers.application.exceptions import GroupInUseError

CORRELATION_ID = str(uuid4())


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


class TestDeleteGroupSuccess:
    """Tests de éxito del Use Case DeleteGroup."""

    @pytest.mark.asyncio
    async def test_delete_group_calls_repo_delete(self):
        """Test 1: DeleteGroup llama a repo.delete con el id correcto."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_group()
        repo.has_active_pipeline_executions.return_value = False

        use_case = DeleteGroup(group_repository=repo)

        await use_case.execute(
            user_id="user-123",
            group_id="grp-123",
            correlation_id=CORRELATION_ID,
        )

        repo.delete.assert_called_once_with("grp-123")

    @pytest.mark.asyncio
    async def test_delete_group_returns_none(self):
        """Test 2: DeleteGroup devuelve None tras eliminar el grupo."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_group()
        repo.has_active_pipeline_executions.return_value = False

        use_case = DeleteGroup(group_repository=repo)

        result = await use_case.execute(
            user_id="user-123",
            group_id="grp-123",
            correlation_id=CORRELATION_ID,
        )

        assert result is None


class TestDeleteGroupError:
    """Tests de error del Use Case DeleteGroup."""

    @pytest.mark.asyncio
    async def test_delete_group_not_found_raises_error(self):
        """Test 3 (RN-01): Si el grupo no existe o no pertenece al usuario, lanza GroupNotFoundError."""
        repo = AsyncMock()
        repo.find_by_id.return_value = None

        use_case = DeleteGroup(group_repository=repo)

        with pytest.raises(GroupNotFoundError):
            await use_case.execute(
                user_id="user-123",
                group_id="grp-inexistente",
                correlation_id=CORRELATION_ID,
            )

    @pytest.mark.asyncio
    async def test_delete_group_with_active_pipelines_raises_error(self):
        """Test 4 (RN-19): Si el grupo tiene pipelines activos, lanza GroupInUseError."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_group()
        repo.has_active_pipeline_executions.return_value = True

        use_case = DeleteGroup(group_repository=repo)

        with pytest.raises(GroupInUseError):
            await use_case.execute(
                user_id="user-123",
                group_id="grp-123",
                correlation_id=CORRELATION_ID,
            )
