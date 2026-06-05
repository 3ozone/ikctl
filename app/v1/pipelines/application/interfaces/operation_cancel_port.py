"""Port OperationCancelPort — interfaz abstracta para cancelar operaciones cross-module.

Permite al módulo pipelines cancelar operaciones del módulo operations
sin importar su capa de application directamente.
"""
from abc import ABC, abstractmethod


class OperationCancelPort(ABC):
    """Contrato para cancelar una operación individual de otro módulo."""

    @abstractmethod
    async def cancel_operation(self, operation_id: str, user_id: str) -> None:
        """Cancela una operación individual.

        - Si está en pending → cancelled (cancelación limpia).
        - Si está en in_progress → cancelled_unsafe (servidor puede quedar parcial).

        Args:
            operation_id: ID de la operación a cancelar.
            user_id: ID del usuario propietario.
        """