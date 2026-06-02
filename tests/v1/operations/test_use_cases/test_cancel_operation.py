"""Tests para el command CancelOperation — T-11."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.v1.operations.application.commands.cancel_operation import CancelOperation
from app.v1.operations.domain.entities.operation import Operation
from app.v1.operations.domain.exceptions.operation import (
    InvalidOperationTransitionError,
    OperationNotFoundError,
)
from app.v1.operations.domain.value_objects.operation_status import OperationStatus

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_operation(status="pending") -> Operation:
    return Operation(
        id="op-1",
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
        started_at=None,
        finished_at=None,
    )


def make_use_case(operation=None):
    operation_repo = AsyncMock()
    event_bus = AsyncMock()

    operation_repo.find_by_id.return_value = operation

    use_case = CancelOperation(
        operation_repository=operation_repo,
        event_bus=event_bus,
    )
    return use_case, operation_repo, event_bus


class TestCancelOperationSuccess:
    """Casos de éxito al cancelar una operación."""

    @pytest.mark.asyncio
    async def test_cancel_pending_transitions_to_cancelled(self):
        op = make_operation(status="pending")
        uc, op_repo, _ = make_use_case(operation=op)

        result = await uc.execute(operation_id="op-1", user_id="user-1")

        assert result.status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_pending_publishes_event_with_was_unsafe_false(self):
        op = make_operation(status="pending")
        uc, op_repo, event_bus = make_use_case(operation=op)

        await uc.execute(operation_id="op-1", user_id="user-1")

        event = event_bus.publish.call_args[0][0]
        assert event.payload["was_unsafe"] is False

    @pytest.mark.asyncio
    async def test_cancel_in_progress_transitions_to_cancelled_unsafe(self):
        op = make_operation(status="in_progress")
        op.started_at = NOW
        uc, op_repo, _ = make_use_case(operation=op)

        result = await uc.execute(operation_id="op-1", user_id="user-1")

        assert result.status == "cancelled_unsafe"

    @pytest.mark.asyncio
    async def test_cancel_in_progress_publishes_event_with_was_unsafe_true(self):
        op = make_operation(status="in_progress")
        op.started_at = NOW
        uc, op_repo, event_bus = make_use_case(operation=op)

        await uc.execute(operation_id="op-1", user_id="user-1")

        event = event_bus.publish.call_args[0][0]
        assert event.payload["was_unsafe"] is True

    @pytest.mark.asyncio
    async def test_cancel_in_progress_updates_operation_in_repo(self):
        op = make_operation(status="in_progress")
        op.started_at = NOW
        uc, op_repo, event_bus = make_use_case(operation=op)

        await uc.execute(operation_id="op-1", user_id="user-1")

        op_repo.update.assert_awaited_once()
        updated_op = op_repo.update.call_args[0][0]
        assert updated_op.status.value == "cancelled_unsafe"

    @pytest.mark.asyncio
    async def test_cancel_pending_updates_operation_in_repo(self):
        op = make_operation(status="pending")
        uc, op_repo, _ = make_use_case(operation=op)

        await uc.execute(operation_id="op-1", user_id="user-1")

        op_repo.update.assert_awaited_once()
        updated_op = op_repo.update.call_args[0][0]
        assert updated_op.status.value == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_publishes_event_after_update(self):
        op = make_operation(status="pending")
        uc, op_repo, event_bus = make_use_case(operation=op)

        call_order = []
        op_repo.update.side_effect = lambda *a, **kw: call_order.append("update")
        event_bus.publish.side_effect = lambda *a, **kw: call_order.append("publish")

        await uc.execute(operation_id="op-1", user_id="user-1")

        assert call_order == ["update", "publish"]


class TestCancelOperationErrors:
    """Casos de error al cancelar una operación."""

    @pytest.mark.asyncio
    async def test_cancel_not_found_raises_error(self):
        uc, *_ = make_use_case(operation=None)

        with pytest.raises(OperationNotFoundError):
            await uc.execute(operation_id="op-x", user_id="user-1")

    @pytest.mark.asyncio
    async def test_cancel_completed_raises_error(self):
        op = make_operation(status="completed")
        uc, *_ = make_use_case(operation=op)

        with pytest.raises(InvalidOperationTransitionError):
            await uc.execute(operation_id="op-1", user_id="user-1")

    @pytest.mark.asyncio
    async def test_cancel_failed_raises_error(self):
        op = make_operation(status="failed")
        uc, *_ = make_use_case(operation=op)

        with pytest.raises(InvalidOperationTransitionError):
            await uc.execute(operation_id="op-1", user_id="user-1")

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled_raises_error(self):
        op = make_operation(status="cancelled")
        uc, *_ = make_use_case(operation=op)

        with pytest.raises(InvalidOperationTransitionError):
            await uc.execute(operation_id="op-1", user_id="user-1")
