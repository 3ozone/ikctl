"""Command LaunchOperation — T-10."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.v1.operations.application.dtos.operation_dtos import OperationResult
from app.v1.operations.application.exceptions import KitNotUsableError, ServerNotActiveError
from app.v1.operations.application.interfaces.file_cache_repository import FileCacheRepository
from app.v1.operations.application.interfaces.kit_repository import KitRepository
from app.v1.operations.application.interfaces.operation_repository import OperationRepository
from app.v1.operations.application.interfaces.server_repository import ServerRepository
from app.v1.operations.application.interfaces.task_queue import TaskQueue
from app.v1.operations.domain.entities.operation import Operation
from app.v1.operations.domain.events.operation_launched import OperationLaunched
from app.v1.operations.domain.exceptions.operation import OperationNotFoundError
from app.v1.operations.domain.value_objects.operation_status import OperationStatus
from app.v1.shared.application.interfaces.event_bus import EventBus


class LaunchOperation:
    """Crea una operación en estado pending y la encola para ejecución.

    Valida que el servidor esté activo (RN-04) y que el kit sea usable (RN-09).
    Hereda debug_level del kit si no se proporciona explícitamente (RN-13).
    Publica OperationLaunched tras persistir (RN-32).
    """

    def __init__(
        self,
        operation_repository: OperationRepository,
        server_repository: ServerRepository,
        kit_repository: KitRepository,
        task_queue: TaskQueue,
        event_bus: EventBus,
        execute_fn=None,
        commit_fn=None,
    ) -> None:
        self._operation_repo = operation_repository
        self._server_repo = server_repository
        self._kit_repo = kit_repository
        self._task_queue = task_queue
        self._event_bus = event_bus
        self._execute_fn = execute_fn or _execute_operation_placeholder
        self._commit_fn = commit_fn

    async def execute(
        self,
        user_id: str,
        server_id: str,
        kit_id: str,
        debug_level: Optional[str],
        values: Optional[dict] = None,
        sudo: bool = False,
        correlation_id: Optional[str] = None,
    ) -> OperationResult:
        """Lanza una nueva operación.

        Args:
            user_id: ID del usuario que lanza la operación.
            server_id: ID del servidor destino.
            kit_id: ID del kit a ejecutar.
            debug_level: Nivel de debug explícito. Si None hereda del kit.
            values: Valores de configuración del usuario (sobreescriben defaults del kit).
            sudo: Si True, ejecuta los scripts del pipeline con sudo.
            correlation_id: UUID de correlación para trazabilidad.

        Returns:
            OperationResult con los datos de la operación creada.

        Raises:
            OperationNotFoundError: Si el servidor o el kit no existen.
            ServerNotActiveError: Si el servidor está inactivo.
            KitNotUsableError: Si el kit no está sincronizado o fue eliminado.
        """
        server = await self._server_repo.find_by_id_internal(server_id)
        if server is None:
            raise OperationNotFoundError(f"Servidor '{server_id}' no encontrado.")

        if not server.is_active():
            raise ServerNotActiveError(
                f"El servidor '{server_id}' está inactivo. "
                "Solo se pueden lanzar operaciones sobre servidores activos."
            )

        kit = await self._kit_repo.find_by_id_internal(kit_id)
        if kit is None:
            raise OperationNotFoundError(f"Kit '{kit_id}' no encontrado.")

        if not kit.is_usable():
            raise KitNotUsableError(
                f"El kit '{kit_id}' no es utilizable "
                "(no sincronizado o eliminado)."
            )

        # RN-13: debug_level explícito > manifest del kit > "none"
        resolved_debug_level = debug_level if debug_level is not None else kit.debug_level
        if not resolved_debug_level:
            resolved_debug_level = "none"

        # RF-14: values del usuario sobreescriben defaults del kit
        resolved_values = values if values is not None else kit.values

        now = datetime.now(timezone.utc)
        operation_id = str(uuid4())
        correlation_id = correlation_id or str(uuid4())

        operation = Operation(
            id=operation_id,
            user_id=user_id,
            server_id=server_id,
            kit_id=kit_id,
            values=resolved_values,
            sudo=sudo,
            status=OperationStatus("pending"),
            debug_level=resolved_debug_level,
            output="",
            backup_files=(),
            created_at=now,
            updated_at=now,
            started_at=None,
            finished_at=None,
        )

        await self._operation_repo.save(operation)

        await self._event_bus.publish(
            OperationLaunched(
                operation_id=operation_id,
                server_id=server_id,
                kit_id=kit_id,
                user_id=user_id,
                correlation_id=correlation_id,
            )
        )

        if self._task_queue is not None:
            await self._task_queue.enqueue(
                self._execute_fn,
                operation_id,
            )
        else:
            if self._commit_fn:
                await self._commit_fn()
            await self._execute_fn(operation_id)

        return OperationResult(
            operation_id=operation.id,
            user_id=operation.user_id,
            server_id=operation.server_id,
            kit_id=operation.kit_id,
            values=operation.values,
            sudo=operation.sudo,
            status=operation.status.value,
            debug_level=operation.debug_level,
            output=operation.output,
            backup_files=operation.backup_files,
            created_at=operation.created_at,
            updated_at=operation.updated_at,
            started_at=operation.started_at,
            finished_at=operation.finished_at,
        )


async def _execute_operation_placeholder(operation_id: str) -> None:
    """Placeholder — reemplazado por _ExecuteOperation en composition root."""
    pass
