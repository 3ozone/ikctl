"""Tests para la query ListOperations — T-15."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.v1.operations.application.queries.list_operations import ListOperations
from app.v1.operations.domain.entities.operation import Operation
from app.v1.operations.domain.value_objects.operation_status import OperationStatus

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_operation(op_id="op-1", status="completed") -> Operation:
    return Operation(
        id=op_id,
        user_id="user-1",
        server_id="srv-1",
        kit_id="kit-1",
        values={},
        sudo=False,
        status=OperationStatus(status),
        debug_level="none",
        output="",
        backup_files=(),
        created_at=NOW,
        updated_at=NOW,
        started_at=NOW,
        finished_at=NOW,
    )


def make_use_case(items=None, total=0):
    operation_repo = AsyncMock()
    operation_repo.find_all_by_user.return_value = (items or [], total)
    use_case = ListOperations(operation_repository=operation_repo)
    return use_case, operation_repo


class TestListOperationsSuccess:
    """Casos de éxito al listar operaciones."""

    @pytest.mark.asyncio
    async def test_list_returns_paginated_result(self):
        ops = [make_operation("op-1"), make_operation("op-2")]
        uc, _ = make_use_case(items=ops, total=2)

        result = await uc.execute(user_id="user-1", page=1, per_page=10)

        assert result.total == 2
        assert result.page == 1
        assert result.per_page == 10
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_list_passes_filters_to_repo(self):
        uc, op_repo = make_use_case(items=[], total=0)

        await uc.execute(
            user_id="user-1",
            page=2,
            per_page=5,
            server_id="srv-1",
            kit_id="kit-1",
            status="completed",
        )

        op_repo.find_all_by_user.assert_awaited_once_with(
            "user-1", 2, 5,
            server_id="srv-1",
            kit_id="kit-1",
            status="completed",
        )

    @pytest.mark.asyncio
    async def test_list_empty_returns_zero_total(self):
        uc, _ = make_use_case(items=[], total=0)

        result = await uc.execute(user_id="user-1", page=1, per_page=10)

        assert result.total == 0
        assert len(result.items) == 0
