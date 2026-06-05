"""Value Object PipelineStatus — ciclo de vida de una ejecución de pipeline."""
from __future__ import annotations

from dataclasses import dataclass

from app.v1.pipelines.domain.exceptions.pipeline_status import InvalidPipelineStatusError

_VALID_VALUES = frozenset({
    "pending",
    "in_progress",
    "completed",
    "failed",
    "partial",
    "cancelled",
})

_TERMINAL_STATES = frozenset({
    "completed",
    "failed",
    "partial",
    "cancelled",
})


@dataclass(frozen=True)
class PipelineStatus:
    """Estado del ciclo de vida de una PipelineExecution.

    Valores válidos:
        - pending      → creada, esperando ejecución
        - in_progress  → ejecutándose (al menos una operación activa)
        - completed    → todas las operaciones completaron con éxito (terminal)
        - failed       → todas las operaciones fallaron (terminal)
        - partial      → al menos una completó y al menos una falló (terminal)
        - cancelled    → cancelada por el usuario o por timeout (terminal)
    """

    value: str

    def __post_init__(self) -> None:
        if self.value not in _VALID_VALUES:
            raise InvalidPipelineStatusError(
                f"Estado de pipeline inválido: '{self.value}'. "
                f"Valores válidos: {sorted(_VALID_VALUES)}"
            )

    @staticmethod
    def terminal_states() -> frozenset[str]:
        """Devuelve el conjunto de estados terminales."""
        return _TERMINAL_STATES

    def is_terminal(self) -> bool:
        """True si el estado es terminal (completed, failed, partial, cancelled)."""
        return self.value in _TERMINAL_STATES