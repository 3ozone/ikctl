"""Tests para la query GetOperation — T-14."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.v1.operations.application.queries.get_operation import GetOperation
from app.v1.operations.domain.entities.operation import Operation
from app.v1.operations.domain.exceptions.operation import OperationNotFoundError
from app.v1.operations.domain.value_objects.operation_status import OperationStatus

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_operation() -> Operation:
    return Operation(
        id="op-1",
        user_id="user-1",
        server_id="srv-1",
        kit_id="kit-1",
        values={},
        sudo=False,
        status=OperationStatus("completed"),
        debug_level="none",
        output="done",
        backup_files=("/etc/nginx.bak.ikctl",),
        created_at=NOW,
        updated_at=NOW,
        started_at=NOW,
        finished_at=NOW,
    )


def make_use_case(operation=None):
    operation_repo = AsyncMock()
    operation_repo.find_by_id.return_value = operation
    use_case = GetOperation(operation_repository=operation_repo)
    return use_case, operation_repo


class TestGetOperationSuccess:
    """Casos de éxito al obtener una operación."""

    @pytest.mark.asyncio
    async def test_get_returns_operation_result(self):
        op = make_operation()
        op.debug_level = "full"
        op.output = "done"
        uc, _ = make_use_case(operation=op)

        result = await uc.execute(operation_id="op-1", user_id="user-1")

        assert result.operation_id == "op-1"
        assert result.status == "completed"
        assert result.output == "done"

    @pytest.mark.asyncio
    async def test_get_queries_with_ownership(self):
        op = make_operation()
        uc, op_repo = make_use_case(operation=op)

        await uc.execute(operation_id="op-1", user_id="user-1")

        op_repo.find_by_id.assert_awaited_once_with("op-1", "user-1")


class TestGetOperationErrors:
    """Casos de error al obtener una operación."""

    @pytest.mark.asyncio
    async def test_get_not_found_raises_error(self):
        uc, _ = make_use_case(operation=None)

        with pytest.raises(OperationNotFoundError):
            await uc.execute(operation_id="op-x", user_id="user-1")


class TestGetOperationOutputFiltering:
    """RF-15: El output se filtra según debug_level."""

    @pytest.mark.asyncio
    async def test_debug_level_none_returns_empty_output(self):
        op = make_operation()
        op.debug_level = "none"
        op.output = "line 1\n[stderr] error msg\nline 3"
        uc, _ = make_use_case(operation=op)

        result = await uc.execute(operation_id="op-1", user_id="user-1")

        assert result.output == ""

    @pytest.mark.asyncio
    async def test_debug_level_errors_returns_only_stderr(self):
        op = make_operation()
        op.debug_level = "errors"
        op.output = "[snapshot] backup\n[upload] config.toml\n[stderr] permission denied\ninstall.sh done\n[stderr] command not found"
        uc, _ = make_use_case(operation=op)

        result = await uc.execute(operation_id="op-1", user_id="user-1")

        assert "[stderr] permission denied" in result.output
        assert "[stderr] command not found" in result.output
        assert "[snapshot]" not in result.output
        assert "[upload]" not in result.output
        assert "install.sh done" not in result.output

    @pytest.mark.asyncio
    async def test_debug_level_full_returns_all_output(self):
        op = make_operation()
        op.debug_level = "full"
        op.output = "[snapshot] backup\n[upload] config.toml\n[stderr] error\ninstall.sh done"
        uc, _ = make_use_case(operation=op)

        result = await uc.execute(operation_id="op-1", user_id="user-1")

        assert result.output == "[snapshot] backup\n[upload] config.toml\n[stderr] error\ninstall.sh done"

    @pytest.mark.asyncio
    async def test_debug_level_errors_with_no_stderr_returns_empty(self):
        op = make_operation()
        op.debug_level = "errors"
        op.output = "[snapshot] backup\n[upload] config.toml\ninstall.sh done"
        uc, _ = make_use_case(operation=op)

        result = await uc.execute(operation_id="op-1", user_id="user-1")

        assert result.output == ""
