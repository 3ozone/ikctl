"""Command CancelPipelineExecution — cancela una ejecución de pipeline en estado in_progress.

Valida:
- RN-01: ownership — solo el propietario puede cancelar.
- R5: no se puede cancelar si está en estado terminal (completed, failed, partial).
- R6: no se puede cancelar si está en estado pending.
- R2: transición in_progress → cancelled.
- R3: cancela operaciones pendientes (pending → cancelled, in_progress → cancelled_unsafe).
- R4: publica evento PipelineExecutionCancelled.
"""
from __future__ import annotations

from uuid import uuid4

from app.v1.pipelines.application.dtos.pipeline_dtos import PipelineExecutionCancelDTO
from app.v1.pipelines.application.interfaces.operation_cancel_port import OperationCancelPort
from app.v1.pipelines.application.interfaces.operation_repository import OperationRepository
from app.v1.pipelines.application.interfaces.pipeline_execution_repository import (
    PipelineExecutionRepository,
)
from app.v1.pipelines.application.interfaces.pipeline_repository import PipelineRepository
from app.v1.pipelines.domain.events.pipeline_execution_cancelled import PipelineExecutionCancelled
from app.v1.pipelines.domain.exceptions.pipeline import PipelineNotFoundError
from app.v1.pipelines.domain.exceptions.pipeline_execution import (
    PipelineExecutionNotFoundError,
    PipelineExecutionNotCancellableError,
)
from app.v1.shared.application.interfaces.event_bus import EventBus


class CancelPipelineExecution:
    """Cancela una ejecución de pipeline en estado in_progress.

    Raises:
        PipelineNotFoundError: si el pipeline no existe o no pertenece al usuario (R7).
        PipelineExecutionNotFoundError: si la ejecución no existe.
        PipelineExecutionNotCancellableError: si la ejecución no está en in_progress (R5, R6).
    """

    def __init__(
        self,
        pipeline_repository: PipelineRepository,
        execution_repository: PipelineExecutionRepository,
        operation_repository: OperationRepository,
        operation_cancel_port: OperationCancelPort,
        event_bus: EventBus,
    ) -> None:
        self._pipeline_repo = pipeline_repository
        self._execution_repo = execution_repository
        self._operation_repo = operation_repository
        self._operation_cancel_port = operation_cancel_port
        self._event_bus = event_bus

    async def execute(
        self, user_id: str, pipeline_id: str, execution_id: str
    ) -> PipelineExecutionCancelDTO:
        # RN-01: ownership
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

        # Validar que la ejecución pertenece al pipeline
        if execution.pipeline_id != pipeline_id:
            raise PipelineExecutionNotFoundError(
                f"Ejecución '{execution_id}' no pertenece al pipeline '{pipeline_id}'."
            )

        # Transición in_progress → cancelled (R2)
        # Lanza PipelineExecutionNotCancellableError si no está en in_progress (R5, R6)
        execution.cancel()
        await self._execution_repo.update(execution)

        # R3: cancelar operaciones pendientes y en progreso
        for op_id in execution.operation_ids:
            op = await self._operation_repo.find_by_id_internal(op_id)
            if op is None:
                continue
            if op.status.value in ("pending", "in_progress"):
                await self._operation_cancel_port.cancel_operation(op_id, user_id)

        # R4: publicar evento
        event = PipelineExecutionCancelled(
            execution_id=execution.id,
            pipeline_id=pipeline_id,
            user_id=user_id,
            correlation_id=str(uuid4()),
        )
        await self._event_bus.publish(event)

        return PipelineExecutionCancelDTO(
            execution_id=execution.id,
            pipeline_id=pipeline_id,
            user_id=user_id,
            status=execution.status.value,
            finished_at=execution.finished_at,
        )