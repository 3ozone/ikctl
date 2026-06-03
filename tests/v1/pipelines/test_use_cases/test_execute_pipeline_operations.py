"""Tests para la async task ExecutePipelineOperations — T-18."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.v1.pipelines.domain.entities.pipeline import Pipeline
from app.v1.pipelines.domain.entities.pipeline_execution import PipelineExecution
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_status import PipelineStatus
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget
from app.v1.servers.domain.entities.group import Group
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


def make_group(group_id: str = "grp-1", server_ids: list[str] | None = None) -> Group:
    return Group(
        id=group_id,
        user_id="user-1",
        name=f"Group {group_id}",
        description=None,
        server_ids=server_ids or ["srv-2", "srv-3"],
        created_at=NOW,
        updated_at=NOW,
    )


def make_pipeline(
    targets: list[PipelineTarget] | None = None,
    kits: list[PipelineKitConfig] | None = None,
    sudo: bool = False,
    debug_level: str = "none",
) -> Pipeline:
    return Pipeline(
        id="pipe-1",
        user_id="user-1",
        name="Mi Pipeline",
        description=None,
        targets=targets or [PipelineTarget(server_id="srv-1")],
        kits=kits or [PipelineKitConfig(kit_id="kit-1")],
        sudo=sudo,
        debug_level=debug_level,
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


def make_task(
    pipeline: Pipeline | None = None,
    execution: PipelineExecution | None = None,
    server_lookup: dict | None = None,
    group_lookup: dict | None = None,
    op_status_sequence: list[str] | None = None,
):
    """
    op_status_sequence: lista de statuses que devuelve operation_repo.find_by_id_internal.
    Si None, devuelve siempre 'completed'.
    """
    from app.v1.pipelines.application.tasks.execute_pipeline_operations import (
        ExecutePipelineOperations,
    )

    pipeline_repo = AsyncMock()
    execution_repo = AsyncMock()
    server_repo = AsyncMock()
    operation_launcher = AsyncMock()
    operation_repo = AsyncMock()

    pipeline_repo.find_by_id_no_ownership.return_value = pipeline
    execution_repo.find_by_id.return_value = execution

    # Server lookup: server_id → Server | None
    s_lookup = server_lookup or {}
    g_lookup = group_lookup or {}

    async def _find_server(server_id: str):
        return s_lookup.get(server_id)

    async def _find_group(group_id: str):
        return g_lookup.get(group_id)

    server_repo.find_server_by_id_internal.side_effect = _find_server
    server_repo.find_group_by_id_internal.side_effect = _find_group

    async def _find_servers_by_ids(ids: list[str]) -> list[Server]:
        return [s_lookup[sid] for sid in ids if sid in s_lookup]

    server_repo.find_servers_by_ids.side_effect = _find_servers_by_ids

    # Launcher devuelve operation_ids secuenciales
    _op_counter = {"n": 0}

    async def _launch(**kwargs):
        _op_counter["n"] += 1
        return f"op-{_op_counter['n']}"

    operation_launcher.launch.side_effect = _launch

    # Polling: operation_repo devuelve ops con el status indicado
    status_seq = op_status_sequence or ["completed"]
    _seq_idx = {"i": 0}

    async def _find_op(op_id: str):
        op = MagicMock()
        idx = min(_seq_idx["i"], len(status_seq) - 1)
        op.status.value = status_seq[idx]
        op.status.is_terminal.return_value = status_seq[idx] in {
            "completed", "failed", "cancelled", "cancelled_unsafe"
        }
        _seq_idx["i"] += 1
        return op

    operation_repo.find_by_id_internal.side_effect = _find_op

    task = ExecutePipelineOperations(
        pipeline_repository=pipeline_repo,
        execution_repository=execution_repo,
        server_repository=server_repo,
        operation_launcher=operation_launcher,
        operation_repository=operation_repo,
    )
    return task, pipeline_repo, execution_repo, server_repo, operation_launcher, operation_repo


class TestExecutePipelineOperationsSuccess:
    """Casos de éxito de la task de ejecución."""

    @pytest.mark.asyncio
    async def test_launches_one_operation_per_server_kit_combination(self):
        """2 targets × 2 kits = 4 llamadas a OperationLauncher.launch."""
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="srv-1"), PipelineTarget(server_id="srv-2")],
            kits=[PipelineKitConfig(kit_id="kit-1"), PipelineKitConfig(kit_id="kit-2")],
        )
        execution = make_execution()
        servers = {"srv-1": make_server("srv-1"), "srv-2": make_server("srv-2")}
        task, *_, launcher, _ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup=servers,
            op_status_sequence=["completed"] * 4,
        )

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        assert launcher.launch.call_count == 4

    @pytest.mark.asyncio
    async def test_calls_execution_start_before_launching_operations(self):
        """execution.start() debe llamarse antes de lanzar operaciones."""
        pipeline = make_pipeline()
        execution = make_execution()
        call_order = []

        original_start = execution.start

        def _start():
            call_order.append("start")
            original_start()

        execution.start = _start

        task, *_, launcher, _ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup={"srv-1": make_server("srv-1")},
            op_status_sequence=["completed"],
        )

        async def _launch_tracked(**kwargs):
            call_order.append("launch")
            return "op-1"

        launcher.launch.side_effect = _launch_tracked

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        assert call_order.index("start") < call_order.index("launch")

    @pytest.mark.asyncio
    async def test_marks_execution_completed_when_all_ops_completed(self):
        pipeline = make_pipeline()
        execution = make_execution()
        task, _, execution_repo, *_ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup={"srv-1": make_server("srv-1")},
            op_status_sequence=["completed"],
        )

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        assert execution.status.value == "completed"
        execution_repo.update.assert_awaited()

    @pytest.mark.asyncio
    async def test_marks_execution_failed_when_all_ops_failed(self):
        pipeline = make_pipeline()
        execution = make_execution()
        task, *_ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup={"srv-1": make_server("srv-1")},
            op_status_sequence=["failed"],
        )

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        assert execution.status.value == "failed"

    @pytest.mark.asyncio
    async def test_marks_execution_partial_when_mixed_results(self):
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="srv-1"), PipelineTarget(server_id="srv-2")],
        )
        execution = make_execution()
        servers = {"srv-1": make_server("srv-1"), "srv-2": make_server("srv-2")}
        task, *_ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup=servers,
            op_status_sequence=["completed", "failed"],
        )

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        assert execution.status.value == "partial"

    @pytest.mark.asyncio
    async def test_resolves_sudo_per_kit_config(self):
        """RN-14: sudo por kit prioridad sobre global."""
        kits = [
            PipelineKitConfig(kit_id="kit-1", sudo=True),   # override: True
            PipelineKitConfig(kit_id="kit-2", sudo=None),   # hereda global: False
        ]
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="srv-1")],
            kits=kits,
            sudo=False,
        )
        execution = make_execution()
        task, *_, launcher, _ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup={"srv-1": make_server("srv-1")},
            op_status_sequence=["completed"] * 2,
        )

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        calls = launcher.launch.call_args_list
        kit1_call = next(c for c in calls if c.kwargs.get("kit_id") == "kit-1")
        kit2_call = next(c for c in calls if c.kwargs.get("kit_id") == "kit-2")
        assert kit1_call.kwargs["sudo"] is True
        assert kit2_call.kwargs["sudo"] is False

    @pytest.mark.asyncio
    async def test_resolves_debug_level_per_kit_config(self):
        """RN-15: debug_level por kit prioridad sobre global."""
        kits = [
            PipelineKitConfig(kit_id="kit-1", debug_level="full"),  # override
            PipelineKitConfig(kit_id="kit-2", debug_level=None),    # hereda global
        ]
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="srv-1")],
            kits=kits,
            debug_level="none",
        )
        execution = make_execution()
        task, *_, launcher, _ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup={"srv-1": make_server("srv-1")},
            op_status_sequence=["completed"] * 2,
        )

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        calls = launcher.launch.call_args_list
        kit1_call = next(c for c in calls if c.kwargs.get("kit_id") == "kit-1")
        kit2_call = next(c for c in calls if c.kwargs.get("kit_id") == "kit-2")
        assert kit1_call.kwargs["debug_level"] == "full"
        assert kit2_call.kwargs["debug_level"] == "none"

    @pytest.mark.asyncio
    async def test_expands_group_target_to_individual_servers(self):
        """Un target que es un grupo se expande a todos sus servidores."""
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="grp-1")],  # group id
        )
        execution = make_execution()
        group = make_group("grp-1", server_ids=["srv-2", "srv-3"])
        servers = {"srv-2": make_server("srv-2"), "srv-3": make_server("srv-3")}

        task, *_, launcher, _ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup=servers,
            group_lookup={"grp-1": group},
            op_status_sequence=["completed"] * 2,
        )

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        # 1 grupo con 2 servers × 1 kit = 2 operaciones
        assert launcher.launch.call_count == 2

    @pytest.mark.asyncio
    async def test_persists_execution_with_final_status(self):
        """execution_repo.update() debe llamarse con el estado final."""
        pipeline = make_pipeline()
        execution = make_execution()
        task, _, execution_repo, *_ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup={"srv-1": make_server("srv-1")},
            op_status_sequence=["completed"],
        )

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        # Al menos 2 updates: uno tras start(), otro tras mark_finished()
        assert execution_repo.update.await_count >= 2


class TestExecutePipelineOperationsEdgeCases:
    """Casos límite."""

    @pytest.mark.asyncio
    async def test_exits_silently_when_execution_not_found(self):
        task, _, execution_repo, *_ = make_task(execution=None)

        # No debe lanzar excepción
        await task.execute("exec-x")

        execution_repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_timeout_marks_execution_failed(self):
        """Si el polling excede el timeout, la ejecución se marca como failed."""
        pipeline = make_pipeline()
        execution = make_execution()
        task, _, execution_repo, *_ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup={"srv-1": make_server("srv-1")},
            op_status_sequence=["pending"],  # Nunca llega a terminal
        )

        with patch("asyncio.sleep"):
            await task.execute("exec-1", timeout_seconds=0)

        assert execution.status.value == "failed"
        execution_repo.update.assert_awaited()

    @pytest.mark.asyncio
    async def test_on_launch_error_marks_execution_failed(self):
        """Si falla el lanzamiento de una operación, la ejecución se marca como failed."""
        pipeline = make_pipeline()
        execution = make_execution()
        task, *_, launcher, _ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup={"srv-1": make_server("srv-1")},
        )
        launcher.launch.side_effect = RuntimeError("SSH connection failed")

        await task.execute("exec-1")

        assert execution.status.value == "failed"
