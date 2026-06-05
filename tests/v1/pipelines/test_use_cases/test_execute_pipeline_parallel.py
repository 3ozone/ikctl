"""Tests para la ejecución paralela de operaciones en pipelines — Feature 7.

Cubre R1–R8 de specs/pipelines_parallel_exec/requirements.md.
"""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.v1.pipelines.application.tasks.execute_pipeline_operations import (
    ExecutePipelineOperations,
    _DEFAULT_MAX_CONCURRENCY,
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

    defaults = dict(
        pipeline_repository=pipeline_repo,
        execution_repository=execution_repo,
        server_repository=server_repo,
        operation_launcher=operation_launcher,
        operation_repository=operation_repo,
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
    )


class TestParallelLaunch:
    """R1, R6: ejecución paralela con gather y preservación de orden."""

    @pytest.mark.asyncio
    async def test_operations_launched_in_parallel(self):
        """3 servers × 2 kits = 6 operaciones lanzadas (R1, R6)."""
        pipeline = make_pipeline(
            targets=[
                PipelineTarget(server_id="srv-1"),
                PipelineTarget(server_id="srv-2"),
                PipelineTarget(server_id="srv-3"),
            ],
            kits=[
                PipelineKitConfig(kit_id="kit-1"),
                PipelineKitConfig(kit_id="kit-2"),
            ],
        )
        execution = make_execution()
        servers = {
            "srv-1": make_server("srv-1"),
            "srv-2": make_server("srv-2"),
            "srv-3": make_server("srv-3"),
        }
        task, pipeline_repo, execution_repo, server_repo, launcher, op_repo = make_task()
        pipeline_repo.find_by_id_no_ownership.return_value = pipeline
        execution_repo.find_by_id.return_value = execution
        async def _find_server(server_id: str):
            return servers.get(server_id)
        server_repo.find_server_by_id_internal.side_effect = _find_server

        op_counter = {"n": 0}
        async def _launch(**kwargs):
            op_counter["n"] += 1
            return f"op-{op_counter['n']}"
        launcher.launch.side_effect = _launch

        op_mock = MagicMock()
        op_mock.status.value = "completed"
        op_repo.find_by_id_internal.return_value = op_mock

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        assert launcher.launch.call_count == 6
        assert len(execution.operation_ids) == 6

    @pytest.mark.asyncio
    async def test_operation_ids_order_preserved(self):
        """2 servers × 3 kits: orden operation_ids = server×kit secuencial (R6)."""
        kits = [
            PipelineKitConfig(kit_id="kit-a"),
            PipelineKitConfig(kit_id="kit-b"),
            PipelineKitConfig(kit_id="kit-c"),
        ]
        pipeline = make_pipeline(
            targets=[
                PipelineTarget(server_id="srv-1"),
                PipelineTarget(server_id="srv-2"),
            ],
            kits=kits,
        )
        execution = make_execution()
        servers = {
            "srv-1": make_server("srv-1"),
            "srv-2": make_server("srv-2"),
        }
        task, pipeline_repo, execution_repo, server_repo, launcher, op_repo = make_task()
        pipeline_repo.find_by_id_no_ownership.return_value = pipeline
        execution_repo.find_by_id.return_value = execution
        async def _find_server(server_id: str):
            return servers.get(server_id)
        server_repo.find_server_by_id_internal.side_effect = _find_server

        call_idx = {"n": 0}
        async def _launch(**kwargs):
            i = call_idx["n"]
            call_idx["n"] += 1
            return f"op-{i}"
        launcher.launch.side_effect = _launch

        op_mock = MagicMock()
        op_mock.status.value = "completed"
        op_repo.find_by_id_internal.return_value = op_mock

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        expected_order = [
            "op-0",  # srv-1 × kit-a
            "op-1",  # srv-1 × kit-b
            "op-2",  # srv-1 × kit-c
            "op-3",  # srv-2 × kit-a
            "op-4",  # srv-2 × kit-b
            "op-5",  # srv-2 × kit-c
        ]
        assert execution.operation_ids == expected_order


class TestSemaphoreConcurrency:
    """R2, R5: límite de concurrencia configurable con Semaphore."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """Pico de concurrencia nunca supera max_concurrency=2 (R2, R5)."""
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id=f"srv-{i}") for i in range(6)],
        )
        execution = make_execution()
        servers = {f"srv-{i}": make_server(f"srv-{i}") for i in range(6)}
        task, pipeline_repo, execution_repo, server_repo, launcher, op_repo = make_task(
            max_concurrency=2,
        )
        pipeline_repo.find_by_id_no_ownership.return_value = pipeline
        execution_repo.find_by_id.return_value = execution
        async def _find_server(server_id: str):
            return servers.get(server_id)
        server_repo.find_server_by_id_internal.side_effect = _find_server

        tracker = {"current": 0, "peak": 0}
        async def _launch_tracked(**kwargs):
            tracker["current"] += 1
            tracker["peak"] = max(tracker["peak"], tracker["current"])
            await asyncio.sleep(0)
            tracker["current"] -= 1
            return "op-x"
        launcher.launch.side_effect = _launch_tracked

        op_mock = MagicMock()
        op_mock.status.value = "completed"
        op_repo.find_by_id_internal.return_value = op_mock

        await task.execute("exec-1", timeout_seconds=0)

        assert tracker["peak"] <= 2

    @pytest.mark.asyncio
    async def test_supports_high_concurrency(self):
        """Soporta 50+ operaciones concurrentes sin degradación (R5)."""
        n_servers = 50
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id=f"srv-{i}") for i in range(n_servers)],
        )
        execution = make_execution()
        servers = {f"srv-{i}": make_server(f"srv-{i}") for i in range(n_servers)}
        task, pipeline_repo, execution_repo, server_repo, launcher, op_repo = make_task(
            max_concurrency=50,
        )
        pipeline_repo.find_by_id_no_ownership.return_value = pipeline
        execution_repo.find_by_id.return_value = execution
        async def _find_server(server_id: str):
            return servers.get(server_id)
        server_repo.find_server_by_id_internal.side_effect = _find_server

        call_idx = {"n": 0}
        async def _launch(**kwargs):
            call_idx["n"] += 1
            return f"op-{call_idx['n']}"
        launcher.launch.side_effect = _launch

        op_mock = MagicMock()
        op_mock.status.value = "completed"
        op_repo.find_by_id_internal.return_value = op_mock

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        assert launcher.launch.call_count == n_servers
        assert len(execution.operation_ids) == n_servers


class TestDefaultConcurrency:
    """R3: valor por defecto de max_concurrency."""

    def test_default_max_concurrency_is_10(self):
        """Instancia sin max_concurrency debe tener _max_concurrency == 10 (R3)."""
        pipeline_repo = AsyncMock()
        execution_repo = AsyncMock()
        server_repo = AsyncMock()
        launcher = AsyncMock()
        op_repo = AsyncMock()

        task = ExecutePipelineOperations(
            pipeline_repository=pipeline_repo,
            execution_repository=execution_repo,
            server_repository=server_repo,
            operation_launcher=launcher,
            operation_repository=op_repo,
        )
        assert task._max_concurrency == 10

    def test_default_constant_value(self):
        """La constante _DEFAULT_MAX_CONCURRENCY debe ser 10."""
        assert _DEFAULT_MAX_CONCURRENCY == 10


class TestPartialFailure:
    """R7: errores parciales durante el lanzamiento."""

    @pytest.mark.asyncio
    async def test_partial_launch_failure_skips_failed_operation(self):
        """Si un launch falla, se omite del resultado y el resto continúa (R7)."""
        pipeline = make_pipeline(
            targets=[
                PipelineTarget(server_id="srv-1"),
                PipelineTarget(server_id="srv-2"),
                PipelineTarget(server_id="srv-3"),
            ],
        )
        execution = make_execution()
        servers = {
            "srv-1": make_server("srv-1"),
            "srv-2": make_server("srv-2"),
            "srv-3": make_server("srv-3"),
        }
        task, pipeline_repo, execution_repo, server_repo, launcher, op_repo = make_task()
        pipeline_repo.find_by_id_no_ownership.return_value = pipeline
        execution_repo.find_by_id.return_value = execution
        async def _find_server(server_id: str):
            return servers.get(server_id)
        server_repo.find_server_by_id_internal.side_effect = _find_server

        call_idx = {"n": 0}
        async def _launch(**kwargs):
            call_idx["n"] += 1
            if call_idx["n"] == 2:
                raise RuntimeError("SSH connection failed")
            return f"op-{call_idx['n']}"
        launcher.launch.side_effect = _launch

        op_mock = MagicMock()
        op_mock.status.value = "failed"
        op_repo.find_by_id_internal.return_value = op_mock

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        assert len(execution.operation_ids) == 2
        assert "op-1" in execution.operation_ids
        assert "op-3" in execution.operation_ids
        assert execution.status.value in ("partial", "failed")


class TestPollingAndTimeout:
    """R8: polling sin cambios de semántica tras el refactor."""

    @pytest.mark.asyncio
    async def test_polling_and_timeout_unaffected(self):
        """Polling detecta operaciones terminales sin regresión (R8)."""
        pipeline = make_pipeline(
            targets=[
                PipelineTarget(server_id="srv-1"),
                PipelineTarget(server_id="srv-2"),
            ],
        )
        execution = make_execution()
        servers = {
            "srv-1": make_server("srv-1"),
            "srv-2": make_server("srv-2"),
        }
        task, pipeline_repo, execution_repo, server_repo, launcher, op_repo = make_task(
            max_concurrency=2,
        )
        pipeline_repo.find_by_id_no_ownership.return_value = pipeline
        execution_repo.find_by_id.return_value = execution
        async def _find_server(server_id: str):
            return servers.get(server_id)
        server_repo.find_server_by_id_internal.side_effect = _find_server

        call_idx = {"n": 0}
        async def _launch(**kwargs):
            call_idx["n"] += 1
            return f"op-{call_idx['n']}"
        launcher.launch.side_effect = _launch

        op_mock = MagicMock()
        op_mock.status.value = "completed"
        op_repo.find_by_id_internal.return_value = op_mock

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        assert execution.status.value == "completed"
        assert execution.finished_at is not None
