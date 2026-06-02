"""Value Object OperationStatus — ciclo de vida de una operación."""
from __future__ import annotations

from dataclasses import dataclass

from app.v1.operations.domain.exceptions.operation import InvalidOperationStatusError


_VALID_VALUES = frozenset({
    "pending",
    "in_progress",
    "completed",
    "failed",
    "cancelled",
    "cancelled_unsafe",
})

_TERMINAL_STATES = frozenset({
    "completed",
    "failed",
    "cancelled",
    "cancelled_unsafe",
})

_RETRIABLE_STATES = frozenset({
    "failed",
    "cancelled_unsafe",
})


@dataclass(frozen=True)
class OperationStatus:
    """Estado del ciclo de vida de una operación.

    Valores válidos:
        - pending          → creada, esperando ejecución
        - in_progress      → ejecutándose en el servidor
        - completed        → finalizada con éxito (terminal)
        - failed           → finalizada con error (terminal, retriable)
        - cancelled        → cancelada desde pending (terminal, limpia)
        - cancelled_unsafe → cancelada desde in_progress (terminal, retriable, servidor parcial)
    """

    value: str

    def __post_init__(self) -> None:
        if self.value not in _VALID_VALUES:
            raise InvalidOperationStatusError(
                f"Estado de operación inválido: '{self.value}'. "
                f"Valores válidos: {sorted(_VALID_VALUES)}"
            )

    @staticmethod
    def terminal_states() -> frozenset[str]:
        """Devuelve el conjunto de estados terminales (no cambian una vez alcanzados)."""
        return _TERMINAL_STATES

    def is_terminal(self) -> bool:
        """True si el estado es terminal (completed, failed, cancelled, cancelled_unsafe)."""
        return self.value in _TERMINAL_STATES

    def is_retriable(self) -> bool:
        """True si se puede reintentar la operación (failed, cancelled_unsafe)."""
        return self.value in _RETRIABLE_STATES
