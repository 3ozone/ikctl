"""Command RestoreOperationBackup — T-12."""
from __future__ import annotations

from typing import Callable, Coroutine

from app.v1.operations.application.dtos.operation_dtos import RestoreResult
from app.v1.operations.application.exceptions import OperationNotRestorableError
from app.v1.operations.application.interfaces.operation_repository import OperationRepository
from app.v1.operations.application.interfaces.task_queue import TaskQueue
from app.v1.operations.domain.exceptions.operation import OperationNotFoundError


async def _restore_backup_placeholder(operation_id: str) -> None:
    """Placeholder — reemplazado en composition root por RestoreBackupTask.execute."""


class RestoreOperationBackup:
    """Encola la restauración de los archivos de backup de una operación fallida.

    Solo se puede restaurar si la operación está en estado failed o cancelled_unsafe
    Y tiene backup_files registrados (is_restorable() == True).

    Raises:
        OperationNotFoundError: Si la operación no existe o no pertenece al usuario.
        OperationNotRestorableError: Si la operación no es restaurable.
    """

    def __init__(
        self,
        operation_repository: OperationRepository,
        task_queue: TaskQueue,
        restore_fn: Callable[..., Coroutine] | None = None,
    ) -> None:
        self._operation_repo = operation_repository
        self._task_queue = task_queue
        self._restore_fn = restore_fn or _restore_backup_placeholder

    async def execute(self, operation_id: str, user_id: str) -> RestoreResult:
        """Encola la restauración del backup de la operación indicada.

        Args:
            operation_id: ID de la operación cuyo backup se restaurará.
            user_id: ID del usuario propietario.

        Returns:
            RestoreResult con el operation_id y los ficheros que serán restaurados.

        Raises:
            OperationNotFoundError: Si la operación no existe o no pertenece al usuario.
            OperationNotRestorableError: Si la operación no es restaurable.
        """
        operation = await self._operation_repo.find_by_id(operation_id, user_id)
        if operation is None:
            raise OperationNotFoundError(
                f"Operación '{operation_id}' no encontrada."
            )

        if not operation.is_restorable():
            raise OperationNotRestorableError(
                f"La operación '{operation_id}' no es restaurable. "
                "Debe estar en estado 'failed' o 'cancelled_unsafe' y tener ficheros de backup."
            )

        await self._task_queue.enqueue(
            self._restore_fn,
            operation_id,
        )

        return RestoreResult(
            operation_id=operation.id,
            restored_files=operation.backup_files,
        )
