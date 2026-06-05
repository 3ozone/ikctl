"""Command LaunchPipeline — T-13.

Lanza una ejecución de un pipeline existente.
Valida:
- RN-01: ownership — solo el propietario puede lanzar.
- RN-09: todos los kits del pipeline deben ser usables (synced + no deleted).
Crea PipelineExecution en estado pending, captura snapshot y encola la task async.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Optional

from app.v1.pipelines.application.dtos.pipeline_dtos import PipelineExecutionResult
from app.v1.pipelines.application.exceptions import PipelineNotLaunchableError
from app.v1.pipelines.application.interfaces.kit_repository import KitRepository
from app.v1.pipelines.application.interfaces.pipeline_execution_repository import (
    PipelineExecutionRepository,
)
from app.v1.pipelines.application.interfaces.pipeline_repository import PipelineRepository
from app.v1.pipelines.domain.entities.pipeline import Pipeline
from app.v1.pipelines.domain.entities.pipeline_execution import PipelineExecution
from app.v1.pipelines.domain.exceptions.pipeline import PipelineNotFoundError
from app.v1.pipelines.domain.value_objects.pipeline_status import PipelineStatus
from app.v1.operations.application.interfaces.task_queue import TaskQueue


async def _execute_pipeline_operations_placeholder(execution_id: str) -> None:
    """Placeholder — sustituido en composition root por ExecutePipelineOperations."""


class LaunchPipeline:
    """Lanza una ejecución del pipeline y la encola para procesamiento async.

    Raises:
        PipelineNotFoundError: si el pipeline no existe o no pertenece al usuario (RN-01).
        PipelineNotLaunchableError: si algún kit no es usable (RN-09).
    """

    def __init__(
        self,
        pipeline_repository: PipelineRepository,
        execution_repository: PipelineExecutionRepository,
        kit_repository: KitRepository,
        task_queue: TaskQueue,
        execute_fn: Optional[Callable[..., Coroutine[Any, Any, None]]] = None,
    ) -> None:
        self._pipeline_repo = pipeline_repository
        self._execution_repo = execution_repository
        self._kit_repo = kit_repository
        self._task_queue = task_queue
        self._execute_fn = execute_fn or _execute_pipeline_operations_placeholder

    async def execute(self, user_id: str, pipeline_id: str) -> PipelineExecutionResult:
        # RN-01: ownership
        pipeline = await self._pipeline_repo.find_by_id(pipeline_id, user_id)
        if pipeline is None:
            raise PipelineNotFoundError(
                f"Pipeline '{pipeline_id}' no encontrado o no pertenece al usuario."
            )

        # RN-09: todos los kits deben ser usables
        await self._validate_kits_usable(pipeline)

        # Captura snapshot inmutable (RN-21)
        snapshot = self._build_snapshot(pipeline)

        execution = PipelineExecution(
            id=str(uuid.uuid4()),
            pipeline_id=pipeline_id,
            user_id=user_id,
            status=PipelineStatus("pending"),
            operation_ids=[],
            snapshot=snapshot,
            created_at=datetime.now(timezone.utc),
        )

        await self._execution_repo.save(execution)
        await self._task_queue.enqueue(self._execute_fn, execution.id)

        return PipelineExecutionResult(
            execution_id=execution.id,
            pipeline_id=pipeline_id,
            user_id=user_id,
            status=execution.status.value,
            snapshot=snapshot,
            created_at=execution.created_at,
        )

    async def _validate_kits_usable(self, pipeline: Pipeline) -> None:
        """RN-09: todos los kits deben estar sincronizados y no eliminados.
        R7: si target tiene kit_ids, deben existir en pipeline.kits.
        """
        for kit_config in pipeline.kits:
            kit = await self._kit_repo.find_by_id_internal(kit_config.kit_id)
            if kit is None or not kit.is_usable():
                raise PipelineNotLaunchableError(
                    f"El kit '{kit_config.kit_id}' no está disponible o no está sincronizado."
                )
        # R7: validar que kit_ids de cada target existan en pipeline.kits
        pipeline_kit_ids = {kc.kit_id for kc in pipeline.kits}
        for target in pipeline.targets:
            if target.kit_ids is not None:
                for kid in target.kit_ids:
                    if kid not in pipeline_kit_ids:
                        raise PipelineNotLaunchableError(
                            f"Kit '{kid}' en target '{target.server_id}' "
                            f"no existe en pipeline.kits."
                        )

    @staticmethod
    def _build_snapshot(pipeline: Pipeline) -> dict:
        """RN-21: captura inmutable de la config del pipeline en el momento del lanzamiento."""
        return {
            "targets": [
                {
                    "server_id": t.server_id,
                    "kit_ids": list(t.kit_ids) if t.kit_ids is not None else None,
                    "values": dict(t.values),
                }
                for t in pipeline.targets
            ],
            "kits": [
                {
                    "kit_id": k.kit_id,
                    "sudo": k.sudo,
                    "debug_level": k.debug_level,
                }
                for k in pipeline.kits
            ],
            "values": dict(pipeline.values),
            "sudo": pipeline.sudo,
            "debug_level": pipeline.debug_level,
        }

