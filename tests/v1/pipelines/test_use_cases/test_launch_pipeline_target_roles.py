"""Tests de target_roles para LaunchPipeline — R3, R7."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.v1.kits.domain.entities.kit import Kit
from app.v1.kits.domain.value_objects.sync_status import SyncStatus
from app.v1.pipelines.application.exceptions import PipelineNotLaunchableError
from app.v1.pipelines.domain.entities.pipeline import Pipeline
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_kit(kit_id: str = "kit-1", synced: bool = True) -> Kit:
    return Kit(
        id=kit_id,
        user_id="user-1",
        repository_id="repo-1",
        path_in_repo="nginx",
        name="Install NGINX",
        description="",
        version="1.0.0",
        tags=[],
        values={},
        debug_level="none",
        upload_files=("install.sh",),
        pipeline_files=("install.sh",),
        backup_files=(),
        sync_status=SyncStatus("synced" if synced else "sync_error"),
        last_synced_at=NOW if synced else None,
        last_commit_sha="abc123" if synced else None,
        sync_error_message=None,
        is_deleted=False,
        created_at=NOW,
        updated_at=NOW,
    )


def make_pipeline(
    pipeline_id: str = "pipe-1",
    targets: list[PipelineTarget] | None = None,
    kits: list[PipelineKitConfig] | None = None,
) -> Pipeline:
    return Pipeline(
        id=pipeline_id,
        user_id="user-1",
        name="Mi Pipeline",
        description=None,
        targets=targets or [PipelineTarget(server_id="srv-1")],
        kits=kits or [PipelineKitConfig(kit_id="kit-1")],
        sudo=False,
        debug_level="none",
        values={"env": "prod"},
        created_at=NOW,
        updated_at=NOW,
    )


def make_use_case(existing_pipeline: Pipeline | None = None, kit_lookup: dict | None = None):
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


class TestLaunchPipelineSnapshotTargetRoles:
    """R3: snapshot captura kit_ids y values por target."""

    @pytest.mark.asyncio
    async def test_snapshot_includes_kit_ids_and_values_per_target(self):
        pipeline = make_pipeline(
            targets=[
                PipelineTarget(server_id="srv-1", kit_ids=("kit-1",), values={"dc": "us-east"}),
                PipelineTarget(server_id="srv-2", kit_ids=None, values={"dc": "us-west"}),
            ],
            kits=[PipelineKitConfig(kit_id="kit-1"), PipelineKitConfig(kit_id="kit-2")],
        )
        kit1 = make_kit("kit-1", synced=True)
        kit2 = make_kit("kit-2", synced=True)
        uc, _, execution_repo, _, _ = make_use_case(
            existing_pipeline=pipeline,
            kit_lookup={"kit-1": kit1, "kit-2": kit2},
        )

        await uc.execute(user_id="user-1", pipeline_id="pipe-1")

        saved = execution_repo.save.call_args[0][0]
        targets_in_snapshot = saved.snapshot["targets"]
        assert len(targets_in_snapshot) == 2
        assert targets_in_snapshot[0]["server_id"] == "srv-1"
        assert targets_in_snapshot[0]["kit_ids"] == ["kit-1"]
        assert targets_in_snapshot[0]["values"] == {"dc": "us-east"}
        assert targets_in_snapshot[1]["server_id"] == "srv-2"
        assert targets_in_snapshot[1]["kit_ids"] is None
        assert targets_in_snapshot[1]["values"] == {"dc": "us-west"}

    @pytest.mark.asyncio
    async def test_snapshot_kit_ids_none_when_not_set(self):
        """Compatibilidad: target sin kit_ids tiene kit_ids: null en snapshot."""
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="srv-1")],
        )
        kit1 = make_kit("kit-1", synced=True)
        uc, _, execution_repo, _, _ = make_use_case(
            existing_pipeline=pipeline,
            kit_lookup={"kit-1": kit1},
        )

        await uc.execute(user_id="user-1", pipeline_id="pipe-1")

        saved = execution_repo.save.call_args[0][0]
        assert saved.snapshot["targets"][0]["kit_ids"] is None
        assert saved.snapshot["targets"][0]["values"] == {}


class TestLaunchPipelineRejectsInvalidTargetKitIds:
    """R7: target con kit_ids inválido lanza PipelineNotLaunchableError."""

    @pytest.mark.asyncio
    async def test_rejects_target_with_nonexistent_kit_id(self):
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="srv-1", kit_ids=("kit-nonexistent",))],
            kits=[PipelineKitConfig(kit_id="kit-1")],
        )
        kit1 = make_kit("kit-1", synced=True)
        uc, _, _, _, _ = make_use_case(
            existing_pipeline=pipeline,
            kit_lookup={"kit-1": kit1},
        )

        with pytest.raises(PipelineNotLaunchableError) as exc:
            await uc.execute(user_id="user-1", pipeline_id="pipe-1")
        assert "kit-nonexistent" in str(exc.value)
        assert "srv-1" in str(exc.value)

    @pytest.mark.asyncio
    async def test_accepts_target_with_valid_kit_ids(self):
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="srv-1", kit_ids=("kit-1",))],
            kits=[PipelineKitConfig(kit_id="kit-1")],
        )
        kit1 = make_kit("kit-1", synced=True)
        uc, _, execution_repo, _, _ = make_use_case(
            existing_pipeline=pipeline,
            kit_lookup={"kit-1": kit1},
        )

        await uc.execute(user_id="user-1", pipeline_id="pipe-1")
        execution_repo.save.assert_awaited_once()
