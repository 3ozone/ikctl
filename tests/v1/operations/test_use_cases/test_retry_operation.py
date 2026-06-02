"""Tests para el command RetryOperation — T-13."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.v1.operations.application.commands.retry_operation import RetryOperation
from app.v1.operations.application.exceptions import OperationNotRetriableError
from app.v1.operations.domain.entities.operation import Operation
from app.v1.operations.domain.exceptions.operation import OperationNotFoundError
from app.v1.operations.domain.value_objects.operation_status import OperationStatus

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_operation(status="failed") -> Operation:
    return Operation(
        id="op-1",
        user_id="user-1",
        server_id="srv-1",
        kit_id="kit-1",
        values={"port": 8080},
        sudo=True,
        status=OperationStatus(status),
        debug_level="verbose",
        output="error: timeout",
        backup_files=("/etc/nginx.bak.ikctl",),
        created_at=NOW,
        updated_at=NOW,
        started_at=NOW,
        finished_at=NOW,
    )


def make_use_case(operation=None):
    operation_repo = AsyncMock()
    task_queue = AsyncMock()
    event_bus = AsyncMock()

    operation_repo.find_by_id.return_value = operation

    use_case = RetryOperation(
        operation_repository=operation_repo,
        task_queue=task_queue,
        event_bus=event_bus,
    )
    return use_case, operation_repo, task_queue, event_bus


class TestRetryOperationSuccess:
    """Casos de éxito al reintentar una operación."""

    @pytest.mark.asyncio
    async def test_retry_creates_new_operation_in_pending(self):
        op = make_operation(status="failed")
        uc, op_repo, *_ = make_use_case(operation=op)

        result = await uc.execute(operation_id="op-1", user_id="user-1")

        op_repo.save.assert_awaited_once()
        saved_op = op_repo.save.call_args[0][0]
        assert saved_op.status.value == "pending"
        assert saved_op.server_id == "srv-1"
        assert saved_op.kit_id == "kit-1"
        assert saved_op.user_id == "user-1"
        assert saved_op.id != "op-1"  # nueva operación, ID distinto

    @pytest.mark.asyncio
    async def test_retry_enqueues_task(self):
        op = make_operation(status="cancelled_unsafe")
        uc, _, task_queue, _ = make_use_case(operation=op)

        await uc.execute(operation_id="op-1", user_id="user-1")

        task_queue.enqueue.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retry_publishes_event_after_save(self):
        op = make_operation(status="failed")
        uc, op_repo, _, event_bus = make_use_case(operation=op)

        call_order = []
        op_repo.save.side_effect = lambda *a, **kw: call_order.append("save")
        event_bus.publish.side_effect = lambda *a, **kw: call_order.append("publish")

        await uc.execute(operation_id="op-1", user_id="user-1")

        assert call_order == ["save", "publish"]


class TestRetryOperationErrors:
    """Casos de error al reintentar una operación."""

    @pytest.mark.asyncio
    async def test_retry_not_found_raises_error(self):
        uc, *_ = make_use_case(operation=None)

        with pytest.raises(OperationNotFoundError):
            await uc.execute(operation_id="op-x", user_id="user-1")

    @pytest.mark.asyncio
    async def test_retry_not_retriable_raises_error(self):
        op = make_operation(status="completed")
        uc, *_ = make_use_case(operation=op)

        with pytest.raises(OperationNotRetriableError):
            await uc.execute(operation_id="op-1", user_id="user-1")
