"""Async task ExecutePipelineOperations — T-18.

Orquesta la ejecución de un pipeline:
1. Carga el pipeline y la ejecución.
2. Marca la ejecución como in_progress.
3. Expande targets (servidores directos + grupos).
4. Lanza N servidores × M kits = N×M operaciones via OperationLauncher.
5. Hace polling hasta que todas las operaciones son terminales (con timeout).
6. Calcula estado agregado (RN-20) y persiste el resultado.

Si falla el lanzamiento o se excede el timeout, marca la ejecución como failed.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.v1.pipelines.application.interfaces.operation_launcher import OperationLauncher
from app.v1.pipelines.application.interfaces.operation_repository import OperationRepository
from app.v1.pipelines.application.interfaces.pipeline_execution_repository import (
    PipelineExecutionRepository,
)
from app.v1.pipelines.application.interfaces.pipeline_repository import PipelineRepository
from app.v1.pipelines.application.interfaces.server_repository import ServerRepository
from app.v1.pipelines.domain.value_objects.pipeline_status import PipelineStatus

_POLL_INTERVAL_SECONDS = 5
_DEFAULT_TIMEOUT_SECONDS = 1800  # 30 minutes (RNF-08)
_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled", "cancelled_unsafe"})

logger = logging.getLogger(__name__)


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
        timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._pipeline_repo = pipeline_repository
        self._execution_repo = execution_repository
        self._server_repo = server_repository
        self._launcher = operation_launcher
        self._operation_repo = operation_repository
        self._timeout_seconds = timeout_seconds

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

            # Lanzar N servidores × M kits = N×M operaciones
            operation_ids: list[str] = []
            for server_id in server_ids:
                for kit_config in pipeline.kits:
                    op_id = await self._launcher.launch(
                        user_id=execution.user_id,
                        server_id=server_id,
                        kit_id=kit_config.kit_id,
                        values={**dict(pipeline.values), **dict(kit_config.values)},
                        sudo=pipeline.resolved_sudo_for(kit_config.kit_id),
                        debug_level=pipeline.resolved_debug_level_for(kit_config.kit_id),
                    )
                    operation_ids.append(op_id)

            execution.operation_ids = operation_ids
            await self._execution_repo.update(execution)

            # Polling hasta que todas las operaciones sean terminales (con timeout)
            final_statuses = await self._poll_until_all_terminal(
                operation_ids, timeout_seconds=effective_timeout
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
            execution.status = PipelineStatus("failed")
            execution.finished_at = datetime.now(timezone.utc)
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

    async def _poll_until_all_terminal(
        self, operation_ids: list[str], timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS
    ) -> list[str]:
        """Hace polling sobre las operaciones hasta que todas son terminales.

        Si se excede timeout_seconds, lanza asyncio.TimeoutError.
        """
        pending = list(operation_ids)
        final_statuses: dict[str, str] = {}
        elapsed = 0

        while pending:
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
                    raise asyncio.TimeoutError(
                        f"Pipeline polling timed out after {timeout_seconds}s "
                        f"with {len(pending)} operations still pending."
                    )
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)
                elapsed += _POLL_INTERVAL_SECONDS

        return [final_statuses[op_id] for op_id in operation_ids]


async def execute_pipeline_operations(execution_id: str) -> None:
    """Función stub para compatibilidad. Reemplazar en composition root."""
    raise NotImplementedError(
        "execute_pipeline_operations debe ser reemplazado por ExecutePipelineOperations "
        "via inyección de dependencias en el composition root."
    )
