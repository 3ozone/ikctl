"""Tests para las queries GetPipeline (T-14) y ListPipelines (T-15)."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

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
        description="Descripción",
        targets=[PipelineTarget(server_id="srv-1")],
        kits=[PipelineKitConfig(kit_id="kit-1")],
        sudo=False,
        debug_level="none",
        values={},
        created_at=NOW,
        updated_at=NOW,
    )


# ---------------------------------------------------------------------------
# T-14: GetPipeline
# ---------------------------------------------------------------------------

class TestGetPipeline:
    def make_use_case(self, pipeline: Pipeline | None):
        from app.v1.pipelines.application.queries.get_pipeline import GetPipeline

        repo = AsyncMock()
        repo.find_by_id.return_value = pipeline
        return GetPipeline(pipeline_repository=repo), repo

    @pytest.mark.asyncio
    async def test_get_returns_pipeline_result(self):
        pipeline = make_pipeline()
        uc, _ = self.make_use_case(pipeline)

        result = await uc.execute(user_id="user-1", pipeline_id="pipe-1")

        assert result.pipeline_id == "pipe-1"
        assert result.name == "Mi Pipeline"
        assert result.user_id == "user-1"

    @pytest.mark.asyncio
    async def test_get_raises_when_pipeline_not_found(self):
        uc, _ = self.make_use_case(None)

        with pytest.raises(PipelineNotFoundError):
            await uc.execute(user_id="user-1", pipeline_id="pipe-x")


# ---------------------------------------------------------------------------
# T-15: ListPipelines
# ---------------------------------------------------------------------------

class TestListPipelines:
    def make_use_case(self, pipelines: list[Pipeline], total: int):
        from app.v1.pipelines.application.queries.list_pipelines import ListPipelines

        repo = AsyncMock()
        repo.find_all_by_user.return_value = (pipelines, total)
        return ListPipelines(pipeline_repository=repo), repo

    @pytest.mark.asyncio
    async def test_list_returns_paginated_result(self):
        pipelines = [make_pipeline("pipe-1"), make_pipeline("pipe-2")]
        uc, _ = self.make_use_case(pipelines, total=2)

        result = await uc.execute(user_id="user-1", page=1, per_page=10)

        assert result.total == 2
        assert result.page == 1
        assert result.per_page == 10
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_list_returns_empty_when_no_pipelines(self):
        uc, _ = self.make_use_case([], total=0)

        result = await uc.execute(user_id="user-1", page=1, per_page=10)

        assert result.total == 0
        assert len(result.items) == 0
