"""Tests para el command LaunchPipeline — T-13."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, call

import pytest

from app.v1.kits.domain.entities.kit import Kit
from app.v1.kits.domain.value_objects.sync_status import SyncStatus
from app.v1.pipelines.application.exceptions import PipelineNotLaunchableError
from app.v1.pipelines.domain.entities.pipeline import Pipeline
from app.v1.pipelines.domain.exceptions.pipeline import PipelineNotFoundError
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_kit(kit_id: str = "kit-1", synced: bool = True, deleted: bool = False) -> Kit:
    return Kit(
        id=kit_id,
        user_id="user-1",
        repository_id="repo-1",
        path_in_repo="nginx",
        name="Install NGINX",
        description="",
        version="1.0.0",
        tags=[],
        values={"port": 80},
        debug_level="none",
        upload_files=("install.sh",),
        pipeline_files=("install.sh",),
        backup_files=("/etc/nginx/nginx.conf",),
        sync_status=SyncStatus("synced" if synced else "sync_error"),
        last_synced_at=NOW if synced else None,
        last_commit_sha="abc123" if synced else None,
        sync_error_message=None,
        is_deleted=deleted,
        created_at=NOW,
        updated_at=NOW,
    )


def make_pipeline(
    pipeline_id: str = "pipe-1",
    kit_ids: list[str] | None = None,
) -> Pipeline:
    kit_ids = kit_ids or ["kit-1"]
    return Pipeline(
        id=pipeline_id,
        user_id="user-1",
        name="Mi Pipeline",
        description=None,
        targets=[PipelineTarget(server_id="srv-1")],
        kits=[PipelineKitConfig(kit_id=k) for k in kit_ids],
        sudo=False,
        debug_level="none",
        values={"env": "prod"},
        created_at=NOW,
        updated_at=NOW,
    )


def make_use_case(
    existing_pipeline: Pipeline | None = None,
    kit_lookup: dict | None = None,
):
    from app.v1.pipelines.application.commands.launch_pipeline import LaunchPipeline

    pipeline_repo = AsyncMock()
    execution_repo = AsyncMock()
    kit_repo = AsyncMock()
    task_queue = AsyncMock()

    pipeline_repo.find_by_id.return_value = existing_pipeline

    lookup = kit_lookup or {}

    async def _find_kit(kit_id: str):
        return lookup.get(kit_id)

    kit_repo.find_by_id_internal.side_effect = _find_kit

    use_case = LaunchPipeline(
        pipeline_repository=pipeline_repo,
        execution_repository=execution_repo,
        kit_repository=kit_repo,
        task_queue=task_queue,
    )
    return use_case, pipeline_repo, execution_repo, kit_repo, task_queue


class TestLaunchPipelineSuccess:
    """Casos de éxito al lanzar un pipeline."""

    @pytest.mark.asyncio
    async def test_launch_returns_execution_result_with_pending_status(self):
        pipeline = make_pipeline()
        kit = make_kit("kit-1", synced=True)
        uc, _, _, _, _ = make_use_case(
            existing_pipeline=pipeline,
            kit_lookup={"kit-1": kit},
        )

        result = await uc.execute(user_id="user-1", pipeline_id="pipe-1")

        assert result.pipeline_id == "pipe-1"
        assert result.user_id == "user-1"
        assert result.status == "pending"
        assert isinstance(result.execution_id, str)
        assert len(result.execution_id) > 0

    @pytest.mark.asyncio
    async def test_launch_persists_execution_via_repository(self):
        pipeline = make_pipeline()
        kit = make_kit("kit-1", synced=True)
        uc, _, execution_repo, _, _ = make_use_case(
            existing_pipeline=pipeline,
            kit_lookup={"kit-1": kit},
        )

        await uc.execute(user_id="user-1", pipeline_id="pipe-1")

        execution_repo.save.assert_awaited_once()
        saved = execution_repo.save.call_args[0][0]
        assert saved.pipeline_id == "pipe-1"
        assert saved.status.value == "pending"

    @pytest.mark.asyncio
    async def test_launch_snapshot_contains_current_pipeline_config(self):
        pipeline = make_pipeline()
        kit = make_kit("kit-1", synced=True)
        uc, _, execution_repo, _, _ = make_use_case(
            existing_pipeline=pipeline,
            kit_lookup={"kit-1": kit},
        )

        await uc.execute(user_id="user-1", pipeline_id="pipe-1")

        saved = execution_repo.save.call_args[0][0]
        assert "targets" in saved.snapshot
        assert "kits" in saved.snapshot
        assert "values" in saved.snapshot
        assert saved.snapshot["values"] == {"env": "prod"}

    @pytest.mark.asyncio
    async def test_launch_enqueues_execute_pipeline_operations_task(self):
        pipeline = make_pipeline()
        kit = make_kit("kit-1", synced=True)
        uc, _, _, _, task_queue = make_use_case(
            existing_pipeline=pipeline,
            kit_lookup={"kit-1": kit},
        )

        await uc.execute(user_id="user-1", pipeline_id="pipe-1")

        task_queue.enqueue.assert_awaited_once()


class TestLaunchPipelineErrors:
    """Casos de error al lanzar un pipeline."""

    @pytest.mark.asyncio
    async def test_launch_raises_when_pipeline_not_found(self):
        """RN-01: solo se puede lanzar el propio pipeline."""
        uc, _, _, _, _ = make_use_case(existing_pipeline=None)

        with pytest.raises(PipelineNotFoundError):
            await uc.execute(user_id="user-1", pipeline_id="pipe-x")

    @pytest.mark.asyncio
    async def test_launch_raises_when_kit_not_usable(self):
        """RN-09: todos los kits del pipeline deben estar sincronizados."""
        pipeline = make_pipeline(kit_ids=["kit-1"])
        unsynced_kit = make_kit("kit-1", synced=False)
        uc, _, _, _, _ = make_use_case(
            existing_pipeline=pipeline,
            kit_lookup={"kit-1": unsynced_kit},
        )

        with pytest.raises(PipelineNotLaunchableError):
            await uc.execute(user_id="user-1", pipeline_id="pipe-1")
