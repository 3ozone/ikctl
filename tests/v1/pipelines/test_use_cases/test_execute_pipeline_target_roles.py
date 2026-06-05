"""Tests de target_roles para ExecutePipelineOperations — R4, R5, R9, R10."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
    values: dict | None = None,
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
        values=values or {},
        created_at=NOW,
        updated_at=NOW,
    )


def make_execution() -> PipelineExecution:
    return PipelineExecution(
        id="exec-1",
        pipeline_id="pipe-1",
        user_id="user-1",
        status=PipelineStatus("pending"),
        operation_ids=[],
        snapshot={},
        created_at=NOW,
    )


def make_task(
    pipeline: Pipeline | None = None,
    execution: PipelineExecution | None = None,
    server_lookup: dict | None = None,
    op_status_sequence: list[str] | None = None,
):
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

    s_lookup = server_lookup or {}

    async def _find_server(server_id: str):
        return s_lookup.get(server_id)

    async def _find_group(group_id: str):
        return None

    server_repo.find_server_by_id_internal.side_effect = _find_server
    server_repo.find_group_by_id_internal.side_effect = _find_group

    async def _find_servers_by_ids(ids: list[str]) -> list[Server]:
        return [s_lookup[sid] for sid in ids if sid in s_lookup]

    server_repo.find_servers_by_ids.side_effect = _find_servers_by_ids

    _op_counter = {"n": 0}

    async def _launch(**kwargs):
        _op_counter["n"] += 1
        return f"op-{_op_counter['n']}"

    operation_launcher.launch.side_effect = _launch

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


class TestExecutePipelineResolvesKitsPerTarget:
    """R4: ExecutePipelineOperations resuelve kits por target."""

    @pytest.mark.asyncio
    async def test_target_with_kit_ids_only_launches_those_kits(self):
        """Target con kit_ids=("kit-1",) solo ejecuta kit-1."""
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="srv-1", kit_ids=("kit-1",))],
            kits=[
                PipelineKitConfig(kit_id="kit-1"),
                PipelineKitConfig(kit_id="kit-2"),
            ],
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

        assert launcher.launch.call_count == 1
        launcher.launch.assert_awaited_once_with(
            user_id="user-1",
            server_id="srv-1",
            kit_id="kit-1",
            values={},
            sudo=False,
            debug_level="none",
        )

    @pytest.mark.asyncio
    async def test_target_with_kit_ids_none_launches_all_kits(self):
        """R10: target sin kit_ids lanza todos los kits (compatibilidad)."""
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="srv-1", kit_ids=None)],
            kits=[
                PipelineKitConfig(kit_id="kit-1"),
                PipelineKitConfig(kit_id="kit-2"),
            ],
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

        assert launcher.launch.call_count == 2

    @pytest.mark.asyncio
    async def test_target_with_kit_ids_preserves_pipeline_kit_order(self):
        """R9: orden de pipeline.kits preservado."""
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="srv-1", kit_ids=("kit-3", "kit-1"))],
            kits=[
                PipelineKitConfig(kit_id="kit-1"),
                PipelineKitConfig(kit_id="kit-2"),
                PipelineKitConfig(kit_id="kit-3"),
            ],
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
        assert len(calls) == 2
        # Orden de pipeline.kits: kit-1, kit-2, kit-3 → filtrado: kit-1, kit-3
        assert calls[0].kwargs["kit_id"] == "kit-1"
        assert calls[1].kwargs["kit_id"] == "kit-3"

    @pytest.mark.asyncio
    async def test_multiple_targets_with_different_kit_ids(self):
        """Targets distintos ejecutan kits distintos."""
        pipeline = make_pipeline(
            targets=[
                PipelineTarget(server_id="srv-1", kit_ids=("kit-1",)),
                PipelineTarget(server_id="srv-2", kit_ids=("kit-2",)),
            ],
            kits=[
                PipelineKitConfig(kit_id="kit-1"),
                PipelineKitConfig(kit_id="kit-2"),
            ],
        )
        execution = make_execution()
        task, *_, launcher, _ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup={"srv-1": make_server("srv-1"), "srv-2": make_server("srv-2")},
            op_status_sequence=["completed"] * 2,
        )

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        calls = launcher.launch.call_args_list
        assert len(calls) == 2
        srv1_calls = [c for c in calls if c.kwargs["server_id"] == "srv-1"]
        srv2_calls = [c for c in calls if c.kwargs["server_id"] == "srv-2"]
        assert len(srv1_calls) == 1
        assert srv1_calls[0].kwargs["kit_id"] == "kit-1"
        assert len(srv2_calls) == 1
        assert srv2_calls[0].kwargs["kit_id"] == "kit-2"


class TestExecutePipelineMergesValues:
    """R5: merge de values pipeline → target → kit."""

    @pytest.mark.asyncio
    async def test_target_values_override_pipeline_values(self):
        """Target.values hace override de pipeline.values."""
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="srv-1", values={"env": "staging"})],
            kits=[PipelineKitConfig(kit_id="kit-1", values={})],
            values={"env": "global"},
        )
        execution = make_execution()
        task, *_, launcher, _ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup={"srv-1": make_server("srv-1")},
            op_status_sequence=["completed"],
        )

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        launcher.launch.assert_awaited_once()
        merged = launcher.launch.call_args.kwargs["values"]
        assert merged["env"] == "staging"

    @pytest.mark.asyncio
    async def test_kit_values_highest_priority(self):
        """Kit.values tiene máxima prioridad (pipeline → target → kit)."""
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="srv-1", values={"env": "target", "dc": "east"})],
            kits=[PipelineKitConfig(kit_id="kit-1", values={"env": "kit"})],
            values={"env": "global", "dc": "global"},
        )
        execution = make_execution()
        task, *_, launcher, _ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup={"srv-1": make_server("srv-1")},
            op_status_sequence=["completed"],
        )

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        launcher.launch.assert_awaited_once()
        merged = launcher.launch.call_args.kwargs["values"]
        assert merged["env"] == "kit"
        assert merged["dc"] == "east"

    @pytest.mark.asyncio
    async def test_no_target_values_falls_back_to_pipeline_kit(self):
        """Sin target.values, mergea pipeline + kit (compatibilidad R10)."""
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="srv-1")],
            kits=[PipelineKitConfig(kit_id="kit-1", values={"level": "debug"})],
            values={"env": "prod"},
        )
        execution = make_execution()
        task, *_, launcher, _ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup={"srv-1": make_server("srv-1")},
            op_status_sequence=["completed"],
        )

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        launcher.launch.assert_awaited_once()
        merged = launcher.launch.call_args.kwargs["values"]
        assert merged["env"] == "prod"
        assert merged["level"] == "debug"


class TestExecutePipelineNoRegression:
    """R10: sin kit_ids ni values, comportamiento legacy."""

    @pytest.mark.asyncio
    async def test_legacy_pipeline_launches_all_kits_all_targets(self):
        """Targets sin kit_ids lanzan todos los kits (compatibilidad)."""
        pipeline = make_pipeline(
            targets=[
                PipelineTarget(server_id="srv-1"),
                PipelineTarget(server_id="srv-2"),
            ],
            kits=[
                PipelineKitConfig(kit_id="kit-1"),
                PipelineKitConfig(kit_id="kit-2"),
            ],
        )
        execution = make_execution()
        task, *_, launcher, _ = make_task(
            pipeline=pipeline,
            execution=execution,
            server_lookup={"srv-1": make_server("srv-1"), "srv-2": make_server("srv-2")},
            op_status_sequence=["completed"] * 4,
        )

        with patch("asyncio.sleep"):
            await task.execute("exec-1")

        # 2 servers × 2 kits = 4 operaciones
        assert launcher.launch.call_count == 4
