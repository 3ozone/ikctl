"""Command DeletePipeline — T-12.

Elimina un pipeline existente del usuario.
Valida:
- RN-01: ownership — solo el propietario puede eliminar.
- RN-16: sin ejecuciones activas en curso.
"""
from __future__ import annotations

from app.v1.pipelines.application.exceptions import PipelineInProgressError
from app.v1.pipelines.application.interfaces.pipeline_repository import PipelineRepository
from app.v1.pipelines.domain.exceptions.pipeline import PipelineNotFoundError


class DeletePipeline:
    """Elimina un pipeline y lo borra de la persistencia.

    Raises:
        PipelineNotFoundError: si el pipeline no existe o no pertenece al usuario (RN-01).
        PipelineInProgressError: si hay ejecuciones activas (RN-16).
    """

    def __init__(self, pipeline_repository: PipelineRepository) -> None:
        self._pipeline_repo = pipeline_repository

    async def execute(self, user_id: str, pipeline_id: str) -> None:
        # RN-01: ownership
        pipeline = await self._pipeline_repo.find_by_id(pipeline_id, user_id)
        if pipeline is None:
            raise PipelineNotFoundError(
                f"Pipeline '{pipeline_id}' no encontrado o no pertenece al usuario."
            )

        # RN-16: sin ejecuciones activas
        if await self._pipeline_repo.has_active_executions(pipeline_id):
            raise PipelineInProgressError(
                f"El pipeline '{pipeline_id}' tiene ejecuciones activas y no puede eliminarse."
            )

        await self._pipeline_repo.delete(pipeline_id)
