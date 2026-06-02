"""Tests para el command DeletePipeline — T-12."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.v1.pipelines.application.exceptions import PipelineInProgressError
from app.v1.pipelines.domain.entities.pipeline import Pipeline
from app.v1.pipelines.domain.exceptions.pipeline import PipelineNotFoundError
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_pipeline(pipeline_id: str = "pipe-1", user_id: str = "user-1") -> Pipeline:
    return Pipeline(
        id=pipeline_id,
        user_id=user_id,
        name="Mi Pipeline",
        description=None,
        targets=[PipelineTarget(server_id="srv-1")],
        kits=[PipelineKitConfig(kit_id="kit-1")],
        created_at=NOW,
        updated_at=NOW,
    )


def make_use_case(
    existing_pipeline: Pipeline | None = None,
    has_active_executions: bool = False,
):
    from app.v1.pipelines.application.commands.delete_pipeline import DeletePipeline

    pipeline_repo = AsyncMock()
    pipeline_repo.find_by_id.return_value = existing_pipeline
    pipeline_repo.has_active_executions.return_value = has_active_executions

    use_case = DeletePipeline(pipeline_repository=pipeline_repo)
    return use_case, pipeline_repo


class TestDeletePipelineSuccess:
    """Casos de éxito al eliminar un pipeline."""

    @pytest.mark.asyncio
    async def test_delete_calls_repository_delete_once(self):
        pipeline = make_pipeline()
        uc, pipeline_repo = make_use_case(existing_pipeline=pipeline)

        await uc.execute(user_id="user-1", pipeline_id="pipe-1")

        pipeline_repo.delete.assert_awaited_once_with("pipe-1")

    @pytest.mark.asyncio
    async def test_delete_returns_none(self):
        pipeline = make_pipeline()
        uc, _ = make_use_case(existing_pipeline=pipeline)

        result = await uc.execute(user_id="user-1", pipeline_id="pipe-1")

        assert result is None


class TestDeletePipelineErrors:
    """Casos de error al eliminar un pipeline."""

    @pytest.mark.asyncio
    async def test_delete_raises_when_pipeline_not_found(self):
        """RN-01: solo se puede eliminar el propio pipeline."""
        uc, _ = make_use_case(existing_pipeline=None)

        with pytest.raises(PipelineNotFoundError):
            await uc.execute(user_id="user-1", pipeline_id="pipe-x")

    @pytest.mark.asyncio
    async def test_delete_raises_when_pipeline_has_active_executions(self):
        """RN-16: no se puede eliminar si hay ejecuciones activas."""
        pipeline = make_pipeline()
        uc, _ = make_use_case(
            existing_pipeline=pipeline,
            has_active_executions=True,
        )

        with pytest.raises(PipelineInProgressError):
            await uc.execute(user_id="user-1", pipeline_id="pipe-1")
