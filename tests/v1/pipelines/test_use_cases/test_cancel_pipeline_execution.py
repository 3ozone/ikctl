"""Tests para el command CancelPipelineExecution (R1–R7)."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.v1.pipelines.application.commands.cancel_pipeline_execution import (
    CancelPipelineExecution,
)
from app.v1.pipelines.domain.entities.pipeline import Pipeline
from app.v1.pipelines.domain.entities.pipeline_execution import PipelineExecution
from app.v1.pipelines.domain.exceptions.pipeline import PipelineNotFoundError
from app.v1.pipelines.domain.exceptions.pipeline_execution import (
    PipelineExecutionNotCancellableError,
    PipelineExecutionNotFoundError,
)
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_status import PipelineStatus
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget

_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_pipeline(pipeline_id: str = "pipe-1", user_id: str = "user-1") -> Pipeline:
    return Pipeline(
        id=pipeline_id,
        user_id=user_id,
        name="Test Pipeline",
        description=None,
        targets=[PipelineTarget(server_id="srv-1")],
        kits=[PipelineKitConfig(kit_id="kit-1")],
        sudo=False,
        debug_level="none",
        values={},
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_execution(
    execution_id: str = "exec-1",
    pipeline_id: str = "pipe-1",
    user_id: str = "user-1",
    status: str = "in_progress",
    operation_ids: list[str] | None = None,
    started_at: datetime | None = _NOW,
    finished_at: datetime | None = None,
) -> PipelineExecution:
    return PipelineExecution(
        id=execution_id,
        pipeline_id=pipeline_id,
        user_id=user_id,
        status=PipelineStatus(status),
        operation_ids=operation_ids or [],
        snapshot={},
        created_at=_NOW,
        started_at=started_at if started_at else (_NOW if status != "pending" else None),
        finished_at=finished_at,
    )


def _make_use_case(
    pipeline=None,
    execution=None,
    op_lookup: dict | None = None,
):
    pipeline_repo = AsyncMock()
    execution_repo = AsyncMock()
    operation_repo = AsyncMock()
    operation_cancel_port = AsyncMock()
    event_bus = AsyncMock()

    pipeline_repo.find_by_id.return_value = pipeline
    execution_repo.find_by_id.return_value = execution

    lookup = op_lookup or {}

    async def _find_op(op_id: str):
        return lookup.get(op_id)

    operation_repo.find_by_id_internal.side_effect = _find_op

    use_case = CancelPipelineExecution(
        pipeline_repository=pipeline_repo,
        execution_repository=execution_repo,
        operation_repository=operation_repo,
        operation_cancel_port=operation_cancel_port,
        event_bus=event_bus,
    )
    return use_case, pipeline_repo, execution_repo, operation_repo, operation_cancel_port, event_bus


class TestCancelInProgressSuccess:
    """Cancelación exitosa de ejecución en progreso (R1, R2, R3)."""

    @pytest.mark.asyncio
    async def test_cancel_in_progress_success(self):
        """R1/R2: cancelar una ejecución in_progress devueve DTO con status cancelled."""
        pipeline = _make_pipeline()
        from unittest.mock import MagicMock

        op1 = MagicMock()
        op1.status.value = "pending"
        op2 = MagicMock()
        op2.status.value = "in_progress"

        execution = _make_execution(operation_ids=["op-1", "op-2"])
        uc, *_, cancel_port, event_bus = _make_use_case(
            pipeline=pipeline,
            execution=execution,
            op_lookup={"op-1": op1, "op-2": op2},
        )

        result = await uc.execute(user_id="user-1", pipeline_id="pipe-1", execution_id="exec-1")

        assert result.status == "cancelled"
        assert result.execution_id == "exec-1"
        assert result.finished_at is not None

    @pytest.mark.asyncio
    async def test_cancel_cancels_pending_operations(self):
        """R3: las operaciones pending se cancelan."""
        pipeline = _make_pipeline()
        from unittest.mock import MagicMock

        op1 = MagicMock()
        op1.status.value = "pending"

        execution = _make_execution(operation_ids=["op-1"])
        uc, *_, cancel_port, _ = _make_use_case(
            pipeline=pipeline,
            execution=execution,
            op_lookup={"op-1": op1},
        )

        await uc.execute(user_id="user-1", pipeline_id="pipe-1", execution_id="exec-1")

        cancel_port.cancel_operation.assert_awaited_once_with("op-1", "user-1")

    @pytest.mark.asyncio
    async def test_cancel_cancels_in_progress_operations(self):
        """R3: las operaciones in_progress se cancelan (cancel_unsafe via port)."""
        pipeline = _make_pipeline()
        from unittest.mock import MagicMock

        op1 = MagicMock()
        op1.status.value = "in_progress"

        execution = _make_execution(operation_ids=["op-1"])
        uc, *_, cancel_port, _ = _make_use_case(
            pipeline=pipeline,
            execution=execution,
            op_lookup={"op-1": op1},
        )

        await uc.execute(user_id="user-1", pipeline_id="pipe-1", execution_id="exec-1")

        cancel_port.cancel_operation.assert_awaited_once_with("op-1", "user-1")

    @pytest.mark.asyncio
    async def test_cancel_skips_terminal_operations(self):
        """R3: las operaciones terminales se saltan."""
        pipeline = _make_pipeline()
        from unittest.mock import MagicMock

        op1 = MagicMock()
        op1.status.value = "completed"

        execution = _make_execution(operation_ids=["op-1"])
        uc, *_, cancel_port, _ = _make_use_case(
            pipeline=pipeline,
            execution=execution,
            op_lookup={"op-1": op1},
        )

        await uc.execute(user_id="user-1", pipeline_id="pipe-1", execution_id="exec-1")

        cancel_port.cancel_operation.assert_not_awaited()


class TestCancelPendingRaises:
    """R6: no se puede cancelar una ejecución en estado pending."""

    @pytest.mark.asyncio
    async def test_cancel_pending_raises_error(self):
        pipeline = _make_pipeline()
        execution = _make_execution(status="pending", started_at=None)

        uc, *_ = _make_use_case(pipeline=pipeline, execution=execution)

        with pytest.raises(PipelineExecutionNotCancellableError):
            await uc.execute(user_id="user-1", pipeline_id="pipe-1", execution_id="exec-1")


class TestCancelTerminalRaises:
    """R5: no se puede cancelar una ejecución en estado terminal."""

    @pytest.mark.asyncio
    async def test_cancel_completed_raises_error(self):
        pipeline = _make_pipeline()
        execution = _make_execution(status="completed", finished_at=_NOW)
        uc, *_ = _make_use_case(pipeline=pipeline, execution=execution)

        with pytest.raises(PipelineExecutionNotCancellableError):
            await uc.execute(user_id="user-1", pipeline_id="pipe-1", execution_id="exec-1")

    @pytest.mark.asyncio
    async def test_cancel_failed_raises_error(self):
        pipeline = _make_pipeline()
        execution = _make_execution(status="failed", finished_at=_NOW)
        uc, *_ = _make_use_case(pipeline=pipeline, execution=execution)

        with pytest.raises(PipelineExecutionNotCancellableError):
            await uc.execute(user_id="user-1", pipeline_id="pipe-1", execution_id="exec-1")


class TestCancelNotOwnerRaises:
    """R7: no se puede cancelar un pipeline que no pertenece al usuario (404)."""

    @pytest.mark.asyncio
    async def test_cancel_not_owner_raises_404(self):
        uc, *_ = _make_use_case(pipeline=None)

        with pytest.raises(PipelineNotFoundError):
            await uc.execute(user_id="user-other", pipeline_id="pipe-1", execution_id="exec-1")


class TestCancelPublishesEvent:
    """R4: cancelar una ejecución publica PipelineExecutionCancelled."""

    @pytest.mark.asyncio
    async def test_cancel_publishes_event(self):
        pipeline = _make_pipeline()
        execution = _make_execution()
        uc, *_, event_bus = _make_use_case(pipeline=pipeline, execution=execution)

        await uc.execute(user_id="user-1", pipeline_id="pipe-1", execution_id="exec-1")

        event_bus.publish.assert_awaited_once()
        event = event_bus.publish.call_args[0][0]
        assert event.event_type == "PipelineExecutionCancelled"
        assert event.aggregate_id == "exec-1"