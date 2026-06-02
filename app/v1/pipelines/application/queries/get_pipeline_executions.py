"""Query GetPipelineExecutions — T-16.

Lista el historial de ejecuciones de un pipeline con paginación.
Valida RN-01: ownership del pipeline.
"""
from __future__ import annotations

from app.v1.pipelines.application.dtos.pipeline_dtos import (
    PipelineExecutionListResult,
    PipelineExecutionSummary,
)
from app.v1.pipelines.application.interfaces.pipeline_execution_repository import (
    PipelineExecutionRepository,
)
from app.v1.pipelines.application.interfaces.pipeline_repository import PipelineRepository
from app.v1.pipelines.domain.entities.pipeline_execution import (
    _COMPLETED_OPERATION_STATUSES,
    _FAILED_OPERATION_STATUSES,
)
from app.v1.pipelines.domain.exceptions.pipeline import PipelineNotFoundError

_TERMINAL_STATUSES = _COMPLETED_OPERATION_STATUSES | _FAILED_OPERATION_STATUSES


class GetPipelineExecutions:
    """Lista ejecuciones de un pipeline paginadas.

    Raises:
        PipelineNotFoundError: si el pipeline no existe o no pertenece al usuario (RN-01).
    """

    def __init__(
        self,
        pipeline_repository: PipelineRepository,
        execution_repository: PipelineExecutionRepository,
    ) -> None:
        self._pipeline_repo = pipeline_repository
        self._execution_repo = execution_repository

    async def execute(
        self,
        user_id: str,
        pipeline_id: str,
        page: int = 1,
        per_page: int = 50,
    ) -> PipelineExecutionListResult:
        # RN-01: ownership
        pipeline = await self._pipeline_repo.find_by_id(pipeline_id, user_id)
        if pipeline is None:
            raise PipelineNotFoundError(
                f"Pipeline '{pipeline_id}' no encontrado o no pertenece al usuario."
            )

        executions, total = await self._execution_repo.find_by_pipeline_id(
            pipeline_id, page, per_page
        )

        items = tuple(
            PipelineExecutionSummary(
                execution_id=ex.id,
                pipeline_id=ex.pipeline_id,
                status=ex.status.value,
                total_operations=len(ex.operation_ids),
                completed_operations=0,   # resumen básico sin cargar ops individuales
                failed_operations=0,
                created_at=ex.created_at,
                started_at=ex.started_at,
                finished_at=ex.finished_at,
            )
            for ex in executions
        )

        return PipelineExecutionListResult(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
        )
