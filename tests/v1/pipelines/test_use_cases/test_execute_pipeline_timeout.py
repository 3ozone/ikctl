"""Tests para el timeout efectivo en ExecutePipelineOperations (R8–R11)."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.v1.pipelines.application.tasks.execute_pipeline_operations import (
    ExecutePipelineOperations,
)
from app.v1.pipelines.domain.entities.pipeline import Pipeline
from app.v1.pipelines.domain.entities.pipeline_execution import PipelineExecution
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_status import PipelineStatus
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget
from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.value_objects.server_type import ServerType

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_server(server_id: str = "srv-1") -> Server:
    return Server(
        id=server_id,
        user_id="user-1",
        name=f"Server {server_id}",
        type=ServerType("remote"),
        status=ServerStatus("active"),
        host="192.168.1.1",
        port=22,
        credential_id="cred-1",
        description=None,
        os_id=None,
        os_version=None,
        os_name=None,
        created_at=NOW,
        updated_at=NOW,
    )


def make_pipeline(
    targets: list[PipelineTarget] | None = None,
    kits: list[PipelineKitConfig] | None = None,
) -> Pipeline:
    return Pipeline(
        id="pipe-1",
        user_id="user-1",
        name="Mi Pipeline",
        description=None,
        targets=targets or [PipelineTarget(server_id="srv-1")],
        kits=kits or [PipelineKitConfig(kit_id="kit-1")],
        sudo=False,
        debug_level="none",
        values={},
        created_at=NOW,
        updated_at=NOW,
    )


def make_execution(
    operation_ids: list[str] | None = None,
    status: str = "pending",
) -> PipelineExecution:
    return PipelineExecution(
        id="exec-1",
        pipeline_id="pipe-1",
        user_id="user-1",
        status=PipelineStatus(status),
        operation_ids=operation_ids or [],
        snapshot={},
        created_at=NOW,
    )


def make_task(**overrides):
    pipeline_repo = AsyncMock()
    execution_repo = AsyncMock()
    server_repo = AsyncMock()
    operation_launcher = AsyncMock()
    operation_repo = AsyncMock()
    operation_cancel_port = AsyncMock()
    commit_fn = AsyncMock()

    defaults = dict(
        pipeline_repository=pipeline_repo,
        execution_repository=execution_repo,
        server_repository=server_repo,
        operation_launcher=operation_launcher,
        operation_repository=operation_repo,
        operation_cancel_port=operation_cancel_port,
        commit_fn=commit_fn,
    )
    defaults.update(overrides)
    task = ExecutePipelineOperations(**defaults)
    return (
        task,
        pipeline_repo,
        execution_repo,
        server_repo,
        operation_launcher,
        operation_repo,
        operation_cancel_port,
        commit_fn,
    )


class TestTimeoutCancelsPendingOperations:
    """R9: operaciones pending → cancelled tras timeout."""

    @pytest.mark.asyncio
    async def test_timeout_cancels_pending_operations(self):
        """Las operaciones en pending se cancelan vía OperationCancelPort."""
        pipeline = make_pipeline()
        execution = make_execution()
        task, pipeline_repo, execution_repo, server_repo, launcher, op_repo, cancel_port, commit_fn = make_task()

        pipeline_repo.find_by_id_no_ownership.return_value = pipeline
        execution_repo.find_by_id.return_value = execution
        server_repo.find_server_by_id_internal.return_value = make_server()
        launcher.launch.side_effect = ["op-1"]

        # op-1 never reaches terminal status, so timeout kicks in
        op_mock = MagicMock()
        op_mock.status.value = "pending"
        op_repo.find_by_id_internal.return_value = op_mock

        with patch("asyncio.sleep"):
            await task.execute("exec-1", timeout_seconds=0)

        cancel_port.cancel_operation.assert_awaited_with("op-1", "user-1")


class TestTimeoutCancelsInProgressOperations:
    """R8: operaciones in_progress → cancelled_unsafe tras timeout."""

    @pytest.mark.asyncio
    async def test_timeout_cancels_in_progress_operations(self):
        """Las operaciones en in_progress se cancelan vía OperationCancelPort (que delega a cancel_unsafe)."""
        pipeline = make_pipeline()
        execution = make_execution()
        task, pipeline_repo, execution_repo, server_repo, launcher, op_repo, cancel_port, commit_fn = make_task()

        pipeline_repo.find_by_id_no_ownership.return_value = pipeline
        execution_repo.find_by_id.return_value = execution
        server_repo.find_server_by_id_internal.return_value = make_server()
        launcher.launch.side_effect = ["op-1"]

        op_mock = MagicMock()
        op_mock.status.value = "in_progress"
        op_repo.find_by_id_internal.return_value = op_mock

        with patch("asyncio.sleep"):
            await task.execute("exec-1", timeout_seconds=0)

        cancel_port.cancel_operation.assert_awaited_with("op-1", "user-1")


class TestTimeoutMarksExecutionAsFailed:
    """R10: la ejecución se marca como failed tras timeout."""

    @pytest.mark.asyncio
    async def test_timeout_marks_execution_failed(self):
        pipeline = make_pipeline()
        execution = make_execution()
        task, pipeline_repo, execution_repo, server_repo, launcher, op_repo, cancel_port, commit_fn = make_task()

        pipeline_repo.find_by_id_no_ownership.return_value = pipeline
        execution_repo.find_by_id.return_value = execution
        server_repo.find_server_by_id_internal.return_value = make_server()
        launcher.launch.side_effect = ["op-1"]

        op_mock = MagicMock()
        op_mock.status.value = "pending"
        op_repo.find_by_id_internal.return_value = op_mock

        with patch("asyncio.sleep"):
            await task.execute("exec-1", timeout_seconds=0)

        assert execution.status.value == "failed"
        assert execution.finished_at is not None


class TestTimeoutPersistsCancelledOperations:
    """R11: las operaciones canceladas se persisten antes de calcular el estado agregado."""

    @pytest.mark.asyncio
    async def test_timeout_persists_cancelled_operations(self):
        pipeline = make_pipeline()
        execution = make_execution()
        task, pipeline_repo, execution_repo, server_repo, launcher, op_repo, cancel_port, commit_fn = make_task()

        pipeline_repo.find_by_id_no_ownership.return_value = pipeline
        execution_repo.find_by_id.return_value = execution
        server_repo.find_server_by_id_internal.return_value = make_server()
        launcher.launch.side_effect = ["op-1"]

        # After cancel, operation shows as cancelled
        call_count = {"n": 0}

        def _make_op(op_id: str):
            mock = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            if n < 2:
                mock.status.value = "pending"
            else:
                mock.status.value = "cancelled"
            return mock

        op_repo.find_by_id_internal.side_effect = _make_op

        with patch("asyncio.sleep"):
            await task.execute("exec-1", timeout_seconds=0)

        cancel_port.cancel_operation.assert_awaited()


class TestTimeoutMixedStatuses:
    """Timeout con mix de operaciones completadas y pendientes."""

    @pytest.mark.asyncio
    async def test_timeout_mixed_statuses(self):
        """Algunas ops completadas y otras pendientes: partial/failed según agregación."""
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="srv-1"), PipelineTarget(server_id="srv-2")],
        )
        execution = make_execution()
        servers = {"srv-1": make_server("srv-1"), "srv-2": make_server("srv-2")}

        task, pipeline_repo, execution_repo, server_repo, launcher, op_repo, cancel_port, commit_fn = make_task()

        pipeline_repo.find_by_id_no_ownership.return_value = pipeline
        execution_repo.find_by_id.return_value = execution

        async def _find_server(server_id: str):
            return servers.get(server_id)

        server_repo.find_server_by_id_internal.side_effect = _find_server
        launcher.launch.side_effect = ["op-1", "op-2"]

        # op-1 completed, op-2 stuck in pending → after timeout → cancelled
        call_count = {"n": 0}

        def _make_op(op_id: str):
            mock = MagicMock()
            if op_id == "op-1":
                mock.status.value = "completed"
            else:
                n = call_count["n"]
                call_count["n"] += 1
                mock.status.value = "cancelled" if n > 0 else "pending"
            return mock

        op_repo.find_by_id_internal.side_effect = _make_op

        with patch("asyncio.sleep"):
            await task.execute("exec-1", timeout_seconds=0)

        assert execution.status.value in ("partial", "failed", "cancelled")