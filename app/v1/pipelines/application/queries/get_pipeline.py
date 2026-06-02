"""Query GetPipeline — T-14.

Devuelve el detalle de un pipeline propio del usuario.
Valida RN-01: ownership.
"""
from __future__ import annotations

from app.v1.pipelines.application.commands.create_pipeline import CreatePipeline
from app.v1.pipelines.application.dtos.pipeline_dtos import PipelineResult
from app.v1.pipelines.application.interfaces.pipeline_repository import PipelineRepository
from app.v1.pipelines.domain.exceptions.pipeline import PipelineNotFoundError


class GetPipeline:
    """Devuelve un pipeline si pertenece al usuario.

    Raises:
        PipelineNotFoundError: si el pipeline no existe o no pertenece al usuario (RN-01).
    """

    def __init__(self, pipeline_repository: PipelineRepository) -> None:
        self._pipeline_repo = pipeline_repository

    async def execute(self, user_id: str, pipeline_id: str) -> PipelineResult:
        pipeline = await self._pipeline_repo.find_by_id(pipeline_id, user_id)
        if pipeline is None:
            raise PipelineNotFoundError(
                f"Pipeline '{pipeline_id}' no encontrado o no pertenece al usuario."
            )
        return CreatePipeline._to_result(pipeline)
