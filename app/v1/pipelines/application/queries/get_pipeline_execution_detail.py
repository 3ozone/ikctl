"""Query GetPipelineExecutionDetail — T-17.

Devuelve el detalle completo de una ejecución: snapshot + lista de operaciones individuales.
Valida RN-01: ownership del pipeline.
"""
from __future__ import annotations

from app.v1.pipelines.application.dtos.pipeline_dtos import (
    PipelineExecutionDetailResult,
    PipelineOperationItem,
)
from app.v1.pipelines.application.interfaces.operation_repository import OperationRepository
from app.v1.pipelines.application.interfaces.pipeline_execution_repository import (
    PipelineExecutionRepository,
)
from app.v1.pipelines.application.interfaces.pipeline_repository import PipelineRepository
from app.v1.pipelines.domain.exceptions.pipeline import PipelineNotFoundError
from app.v1.pipelines.domain.exceptions.pipeline_execution import PipelineExecutionNotFoundError


class GetPipelineExecutionDetail:
    """Devuelve detalle de una ejecución con todas las operaciones individuales.

    Raises:
        PipelineNotFoundError: si el pipeline no existe o no pertenece al usuario (RN-01).
        PipelineExecutionNotFoundError: si la ejecución no existe.
    """

    def __init__(
        self,
        pipeline_repository: PipelineRepository,
        execution_repository: PipelineExecutionRepository,
        operation_repository: OperationRepository,
    ) -> None:
        self._pipeline_repo = pipeline_repository
        self._execution_repo = execution_repository
        self._operation_repo = operation_repository

    async def execute(
        self,
        user_id: str,
        pipeline_id: str,
        execution_id: str,
    ) -> PipelineExecutionDetailResult:
        # RN-01: ownership del pipeline
        pipeline = await self._pipeline_repo.find_by_id(pipeline_id, user_id)
        if pipeline is None:
            raise PipelineNotFoundError(
                f"Pipeline '{pipeline_id}' no encontrado o no pertenece al usuario."
            )

        execution = await self._execution_repo.find_by_id(execution_id)
        if execution is None:
            raise PipelineExecutionNotFoundError(
                f"Ejecución '{execution_id}' no encontrada."
            )

        # Carga operaciones individuales
        op_items = []
        for op_id in execution.operation_ids:
            op = await self._operation_repo.find_by_id_internal(op_id)
            if op is not None:
                op_items.append(
                    PipelineOperationItem(
                        operation_id=op.id,
                        server_id=op.server_id,
                        kit_id=op.kit_id,
                        status=op.status.value,
                        output=op.output,
                        error=None,
                    )
                )

        return PipelineExecutionDetailResult(
            execution_id=execution.id,
            pipeline_id=execution.pipeline_id,
            user_id=execution.user_id,
            status=execution.status.value,
            snapshot=execution.snapshot,
            operations=tuple(op_items),
            created_at=execution.created_at,
            started_at=execution.started_at,
            finished_at=execution.finished_at,
        )
