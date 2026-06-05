"""Async task ExecutePipelineOperations — T-18 + timeout efectivo.

Orquesta la ejecución de un pipeline:
1. Carga el pipeline y la ejecución.
2. Marca la ejecución como in_progress.
3. Expande targets (servidores directos + grupos).
4. Lanza N servidores × M kits = N×M operaciones via OperationLauncher.
5. Hace polling hasta que todas las operaciones son terminales (con timeout).
6. Calcula estado agregado (RN-20) y persiste el resultado.

Si se excede el timeout:
- Las operaciones pending → cancelled (R9).
- Las operaciones in_progress → cancelled_unsafe (R8).
- La ejecución → failed con finished_at (R10).
- Las operaciones canceladas se persisten antes de calcular el estado agregado (R11).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from app.v1.pipelines.application.interfaces.operation_cancel_port import OperationCancelPort
from app.v1.pipelines.application.interfaces.operation_launcher import OperationLauncher
from app.v1.pipelines.application.interfaces.operation_repository import OperationRepository
from app.v1.pipelines.application.interfaces.pipeline_execution_repository import (
    PipelineExecutionRepository,
)
from app.v1.pipelines.application.interfaces.pipeline_repository import PipelineRepository
from app.v1.pipelines.application.interfaces.server_repository import ServerRepository
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_status import PipelineStatus
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget
from app.v1.shared.infrastructure.logger import get_logger

_POLL_INTERVAL_SECONDS = 5
_DEFAULT_TIMEOUT_SECONDS = 1800  # 30 minutes (RNF-08)
_DEFAULT_MAX_CONCURRENCY: int = 10
_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled", "cancelled_unsafe"})

logger = get_logger(__name__)


class ExecutePipelineOperations:
    """Orquesta la ejecución asíncrona de todas las operaciones de un pipeline.

    Diseñado para ser encolado via TaskQueue e inyectado en LaunchPipeline
    como execute_fn.
    """

    def __init__(
        self,
        pipeline_repository: PipelineRepository,
        execution_repository: PipelineExecutionRepository,
        server_repository: ServerRepository,
        operation_launcher: OperationLauncher,
        operation_repository: OperationRepository,
        operation_cancel_port: Optional[OperationCancelPort] = None,
        timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
        commit_fn: Optional[object] = None,
        max_concurrency: int = _DEFAULT_MAX_CONCURRENCY,
    ) -> None:
        self._pipeline_repo = pipeline_repository
        self._execution_repo = execution_repository
        self._server_repo = server_repository
        self._launcher = operation_launcher
        self._operation_repo = operation_repository
        self._operation_cancel_port = operation_cancel_port
        self._timeout_seconds = timeout_seconds
        self._commit_fn = commit_fn
        self._max_concurrency = max_concurrency

    async def execute(self, execution_id: str, timeout_seconds: int | None = None) -> None:
        """Punto de entrada de la task. Silencioso si la ejecución no existe."""
        effective_timeout = timeout_seconds if timeout_seconds is not None else self._timeout_seconds

        execution = await self._execution_repo.find_by_id(execution_id)
        if execution is None:
            return

        pipeline = await self._pipeline_repo.find_by_id_no_ownership(execution.pipeline_id)
        if pipeline is None:
            return

        try:
            # Transición pending → in_progress
            execution.start()
            await self._execution_repo.update(execution)

            # Expandir targets a server_ids individuales
            server_ids = await self._expand_targets(pipeline)

            # Lanzar N servidores × M kits = N×M operaciones en paralelo
            operation_ids = await self._launch_all_operations(
                server_ids, pipeline, execution.user_id
            )

            execution.operation_ids = operation_ids
            await self._execution_repo.update(execution)

            # Polling hasta que todas las operaciones sean terminales (con timeout)
            final_statuses = await self._poll_until_all_terminal(
                operation_ids, execution.user_id, timeout_seconds=effective_timeout
            )

            # RN-20: calcula estado agregado y cierra la ejecución
            execution.mark_finished(final_statuses)
            await self._execution_repo.update(execution)

        except Exception as exc:
            logger.error("pipeline_execution_failed", extra={
                "execution_id": execution_id,
                "error": str(exc),
            })
            if execution.status.value == "pending":
                execution.status = PipelineStatus("in_progress")
                execution.started_at = datetime.now(timezone.utc)
            execution.mark_timeout_failed()
            await self._execution_repo.update(execution)

    async def _expand_targets(self, pipeline) -> list[str]:
        """Expande targets: servidores directos + miembros de grupos."""
        server_ids: list[str] = []
        for target in pipeline.targets:
            target_id = target.server_id
            # Intenta como servidor directo primero
            server = await self._server_repo.find_server_by_id_internal(target_id)
            if server is not None:
                server_ids.append(server.id)
                continue
            # Si no es servidor, intenta como grupo
            group = await self._server_repo.find_group_by_id_internal(target_id)
            if group is not None:
                server_ids.extend(group.server_ids)
        return server_ids

    async def _launch_all_operations(
        self,
        server_ids: list[str],
        pipeline,
        user_id: str,
    ) -> list[str]:
        """Lanza todas las operaciones N×M en paralelo respetando max_concurrency.

        Por cada server_id, resuelve el target original y sus kits específicos
        (R4). Mergea values con precedencia: pipeline → target → kit (R5).
        Preserva el orden original de pipeline.kits (R9).
        """
        semaphore = asyncio.Semaphore(self._max_concurrency)
        tasks: list = []

        for server_id in server_ids:
            target = self._find_target_for_server(server_id, pipeline)
            kits = self._resolve_kits_for_target(target, pipeline)

            for kit_config in kits:
                merged_values = {
                    **dict(pipeline.values),
                    **dict(target.values if target else {}),
                    **dict(kit_config.values),
                }

                async def _bounded_launch(
                    sid: str = server_id,
                    kc = kit_config,
                ) -> str | None:
                    async with semaphore:
                        return await self._launcher.launch(
                            user_id=user_id,
                            server_id=sid,
                            kit_id=kc.kit_id,
                            values=merged_values,
                            sudo=pipeline.resolved_sudo_for(kc.kit_id),
                            debug_level=pipeline.resolved_debug_level_for(kc.kit_id),
                        )
                tasks.append(_bounded_launch())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        operation_ids: list[str] = []
        for idx, result in enumerate(results):
            if isinstance(result, str):
                operation_ids.append(result)
            else:
                exc = result if isinstance(result, BaseException) else Exception("unknown")
                logger.error("pipeline_launch_operation_failed", extra={
                    "operation_idx": idx,
                    "error": str(exc),
                })

        return operation_ids

    def _find_target_for_server(
        self, server_id: str, pipeline,
    ) -> Optional[PipelineTarget]:
        """Busca el PipelineTarget original que corresponde a un server_id expandido."""
        for t in pipeline.targets:
            if t.server_id == server_id:
                return t
        return None

    def _resolve_kits_for_target(
        self, target: Optional[PipelineTarget], pipeline,
    ) -> list[PipelineKitConfig]:
        """Resuelve los kits que aplican a un target.

        Si target tiene kit_ids definido, filtra pipeline.kits preservando orden.
        Si no, devuelve todos (comportamiento legacy).
        """
        if target is None or target.kit_ids is None:
            return list(pipeline.kits)
        kit_ids_set = set(target.kit_ids)
        return [kc for kc in pipeline.kits if kc.kit_id in kit_ids_set]

    async def _poll_until_all_terminal(
        self, operation_ids: list[str], user_id: str, timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS
    ) -> list[str]:
        """Hace polling sobre las operaciones hasta que todas son terminales.

        Si se excede timeout_seconds, cancela las operaciones pendientes/en progreso
        y devuelve los estados finales (incluyendo los cancelados).
        """
        pending = list(operation_ids)
        final_statuses: dict[str, str] = {}
        elapsed = 0

        while pending:
            # Commit antes de leer para empezar una transacción fresca
            # y ver los cambios committeados por otras sesiones (MySQL REPEATABLE READ).
            if self._commit_fn:
                await self._commit_fn()

            still_pending = []
            for op_id in pending:
                op = await self._operation_repo.find_by_id_internal(op_id)
                if op is not None and op.status.value in _TERMINAL_STATUSES:
                    final_statuses[op_id] = op.status.value
                else:
                    still_pending.append(op_id)
            pending = still_pending
            if pending:
                if elapsed >= timeout_seconds:
                    # R8, R9: cancelar operaciones pendientes/en progreso
                    await self._cancel_pending_operations(pending, user_id)
                    # R11: persistir operaciones canceladas
                    if self._commit_fn:
                        await self._commit_fn()
                    # Recoger los estados finales de las operaciones canceladas
                    for op_id in pending:
                        op = await self._operation_repo.find_by_id_internal(op_id)
                        if op is not None:
                            final_statuses[op_id] = op.status.value
                        else:
                            final_statuses[op_id] = "failed"
                    break
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)
                elapsed += _POLL_INTERVAL_SECONDS

        return [final_statuses[op_id] for op_id in operation_ids]

    async def _cancel_pending_operations(self, pending_op_ids: list[str], user_id: str) -> None:
        """Cancela las operaciones que aún no son terminales tras el timeout.

        R8: in_progress → cancelled_unsafe (via OperationCancelPort).
        R9: pending → cancelled (via OperationCancelPort).
        """
        if self._operation_cancel_port is None:
            return
        for op_id in pending_op_ids:
            try:
                await self._operation_cancel_port.cancel_operation(op_id, user_id)
            except Exception as exc:
                logger.warning(
                    "cancel_operation_failed",
                    extra={"operation_id": op_id, "error": str(exc)},
                )


async def execute_pipeline_operations(execution_id: str) -> None:
    """Función stub para compatibilidad. Reemplazar en composition root."""
    raise NotImplementedError(
        "execute_pipeline_operations debe ser reemplazado por ExecutePipelineOperations "
        "via inyección de dependencias en el composition root."
    )