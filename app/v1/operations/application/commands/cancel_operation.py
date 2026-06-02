"""Command CancelOperation — T-11."""
from __future__ import annotations

from datetime import datetime, timezone

from app.v1.operations.application.dtos.operation_dtos import OperationResult
from app.v1.operations.application.interfaces.operation_repository import OperationRepository
from app.v1.operations.domain.events.operation_cancelled import OperationCancelled
from app.v1.operations.domain.exceptions.operation import OperationNotFoundError
from app.v1.operations.domain.value_objects.operation_status import OperationStatus
from app.v1.shared.application.interfaces.event_bus import EventBus
from uuid import uuid4


class CancelOperation:
    """Cancela una operación en estado pending o in_progress.

    - pending → cancelled (cancelación limpia)
    - in_progress → cancelled_unsafe (servidor puede quedar en estado parcial)

    Raises:
        OperationNotFoundError: Si la operación no existe o no pertenece al usuario.
        InvalidOperationTransitionError: Si la operación está en estado terminal.
    """

    def __init__(
        self,
        operation_repository: OperationRepository,
        event_bus: EventBus,
    ) -> None:
        self._operation_repo = operation_repository
        self._event_bus = event_bus

    async def execute(self, operation_id: str, user_id: str) -> OperationResult:
        """Cancela la operación indicada.

        Si la operación está en pending → cancelled (limpio).
        Si la operación está en in_progress → cancelled_unsafe (servidor parcial).

        Args:
            operation_id: ID de la operación a cancelar.
            user_id: ID del usuario propietario.

        Returns:
            OperationResult con el estado actualizado.

        Raises:
            OperationNotFoundError: Si la operación no existe o no pertenece al usuario.
            InvalidOperationTransitionError: Si la operación está en estado terminal.
        """
        operation = await self._operation_repo.find_by_id(operation_id, user_id)
        if operation is None:
            raise OperationNotFoundError(
                f"Operación '{operation_id}' no encontrada."
            )

        now = datetime.now(timezone.utc)
        was_unsafe = operation.status == OperationStatus("in_progress")

        if was_unsafe:
            operation.cancel_unsafe(now)
        else:
            operation.cancel(now)

        await self._operation_repo.update(operation)

        await self._event_bus.publish(
            OperationCancelled(
                operation_id=operation.id,
                user_id=operation.user_id,
                was_unsafe=was_unsafe,
                correlation_id=str(uuid4()),
            )
        )

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
