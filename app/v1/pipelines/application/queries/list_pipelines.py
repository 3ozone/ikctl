"""Query ListPipelines — T-15.

Lista los pipelines del usuario con paginación.
"""
from __future__ import annotations

from app.v1.pipelines.application.commands.create_pipeline import CreatePipeline
from app.v1.pipelines.application.dtos.pipeline_dtos import PipelineListResult
from app.v1.pipelines.application.interfaces.pipeline_repository import PipelineRepository


class ListPipelines:
    """Lista los pipelines del usuario paginados."""

    def __init__(self, pipeline_repository: PipelineRepository) -> None:
        self._pipeline_repo = pipeline_repository

    async def execute(
        self, user_id: str, page: int = 1, per_page: int = 50
    ) -> PipelineListResult:
        pipelines, total = await self._pipeline_repo.find_all_by_user(
            user_id, page, per_page
        )
        return PipelineListResult(
            items=tuple(CreatePipeline._to_result(p) for p in pipelines),
            total=total,
            page=page,
            per_page=per_page,
        )
