"""Command RetryOperation — T-13."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.v1.operations.application.commands.launch_operation import _execute_operation_placeholder

from app.v1.operations.application.dtos.operation_dtos import OperationResult
from app.v1.operations.application.exceptions import OperationNotRetriableError
from app.v1.operations.application.interfaces.operation_repository import OperationRepository
from app.v1.operations.application.interfaces.task_queue import TaskQueue
from app.v1.operations.domain.entities.operation import Operation
from app.v1.operations.domain.events.operation_launched import OperationLaunched
from app.v1.operations.domain.exceptions.operation import OperationNotFoundError
from app.v1.operations.domain.value_objects.operation_status import OperationStatus
from app.v1.shared.application.interfaces.event_bus import EventBus


class RetryOperation:
    """Crea una nueva operación en pending a partir de una fallida o cancelada (unsafe).

    La operación original permanece intacta; se crea una nueva con el mismo
    server_id, kit_id, user_id y debug_level pero con un ID nuevo y estado pending.

    Raises:
        OperationNotFoundError: Si la operación no existe o no pertenece al usuario.
        OperationNotRetriableError: Si la operación no está en estado failed/cancelled_unsafe.
    """

    def __init__(
        self,
        operation_repository: OperationRepository,
        task_queue: TaskQueue,
        event_bus: EventBus,
        execute_fn=None,
    ) -> None:
        self._operation_repo = operation_repository
        self._task_queue = task_queue
        self._event_bus = event_bus
        self._execute_fn = execute_fn or _execute_operation_placeholder

    async def execute(self, operation_id: str, user_id: str) -> OperationResult:
        """Reintenta la operación indicada creando una nueva en estado pending.

        Args:
            operation_id: ID de la operación fallida a reintentar.
            user_id: ID del usuario propietario.

        Returns:
            OperationResult de la nueva operación creada.

        Raises:
            OperationNotFoundError: Si la operación no existe o no pertenece al usuario.
            OperationNotRetriableError: Si la operación no es retriable.
        """
        original = await self._operation_repo.find_by_id(operation_id, user_id)
        if original is None:
            raise OperationNotFoundError(
                f"Operación '{operation_id}' no encontrada."
            )

        if not original.is_retriable():
            raise OperationNotRetriableError(
                f"La operación '{operation_id}' no puede reintentarse. "
                "Solo es posible desde los estados 'failed' o 'cancelled_unsafe'."
            )

        now = datetime.now(timezone.utc)
        new_operation_id = str(uuid4())
        correlation_id = str(uuid4())

        new_operation = Operation(
            id=new_operation_id,
            user_id=original.user_id,
            server_id=original.server_id,
            kit_id=original.kit_id,
            values=original.values,
            sudo=original.sudo,
            status=OperationStatus("pending"),
            debug_level=original.debug_level,
            output="",
            backup_files=(),
            created_at=now,
            updated_at=now,
            started_at=None,
            finished_at=None,
        )

        await self._operation_repo.save(new_operation)

        await self._event_bus.publish(
            OperationLaunched(
                operation_id=new_operation_id,
                server_id=new_operation.server_id,
                kit_id=new_operation.kit_id,
                user_id=new_operation.user_id,
                correlation_id=correlation_id,
            )
        )

        await self._task_queue.enqueue(
            self._execute_fn,
            new_operation_id,
        )

        return OperationResult(
            operation_id=new_operation.id,
            user_id=new_operation.user_id,
            server_id=new_operation.server_id,
            kit_id=new_operation.kit_id,
            values=new_operation.values,
            sudo=new_operation.sudo,
            status=new_operation.status.value,
            debug_level=new_operation.debug_level,
            output=new_operation.output,
            backup_files=new_operation.backup_files,
            created_at=new_operation.created_at,
            updated_at=new_operation.updated_at,
            started_at=new_operation.started_at,
            finished_at=new_operation.finished_at,
        )
