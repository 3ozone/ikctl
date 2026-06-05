"""OperationCancelAdapter — Adapter que delega al CancelOperation del módulo operations.

Implementa el port OperationCancelPort del módulo pipelines, permitiendo
cancelar operaciones sin importar directamente la capa de application de operations.
"""
from app.v1.pipelines.application.interfaces.operation_cancel_port import OperationCancelPort


class OperationCancelAdapter(OperationCancelPort):
    """Adapter que envuelve CancelOperation para cancelar operaciones individuales."""

    def __init__(self, cancel_operation) -> None:
        self._cancel_operation = cancel_operation

    async def cancel_operation(self, operation_id: str, user_id: str) -> None:
        """Delega al CancelOperation command del módulo operations.

        Si la operación está en pending → cancelled.
        Si la operación está en in_progress → cancelled_unsafe.
        """
        await self._cancel_operation.execute(
            operation_id=operation_id,
            user_id=user_id,
        )