"""Entity PipelineExecution — instancia concreta de una ejecución de pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.v1.pipelines.domain.exceptions.pipeline_status import InvalidPipelineStatusError
from app.v1.pipelines.domain.value_objects.pipeline_status import PipelineStatus

_TERMINAL_OPERATION_STATUSES = frozenset({"completed", "failed", "cancelled", "cancelled_unsafe"})
_COMPLETED_OPERATION_STATUSES = frozenset({"completed"})
_FAILED_OPERATION_STATUSES = frozenset({"failed", "cancelled_unsafe", "cancelled"})


@dataclass
class PipelineExecution:
    """Instancia concreta de una ejecución de pipeline.

Ciclo de vida:
        pending → in_progress → completed   (todas ops OK)
                                 failed      (todas ops fallaron)
                                 partial     (mixto)
                                 cancelled   (cancelada por el usuario o timeout)

    RN-20: estado agregado calculado a partir de los estados de las operaciones.
    RN-21: snapshot inmutable de targets+kits+values en el momento del lanzamiento.
    """

    id: str
    pipeline_id: str
    user_id: str
    status: PipelineStatus
    operation_ids: list[str] = field(default_factory=list)
    snapshot: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    def start(self) -> None:
        """Transición pending → in_progress. Registra started_at."""
        if self.status.value != "pending":
            raise InvalidPipelineStatusError(
                f"No se puede iniciar una ejecución en estado '{self.status.value}'. "
                f"Debe estar en estado 'pending'."
            )
        self.status = PipelineStatus("in_progress")
        self.started_at = datetime.now(timezone.utc)

    def mark_finished(self, operation_statuses: list[str]) -> None:
        """RN-20: calcula estado agregado y marca como terminada.

        Args:
            operation_statuses: lista de estados finales de las operaciones generadas.

        Raises:
            InvalidPipelineStatusError: si la ejecución no está en in_progress.
        """
        if self.status.value != "in_progress":
            raise InvalidPipelineStatusError(
                f"No se puede finalizar una ejecución en estado '{self.status.value}'. "
                f"Debe estar en estado 'in_progress'."
            )
        aggregated = self._calculate_aggregated_status(operation_statuses)
        self.status = PipelineStatus(aggregated)
        self.finished_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        """Transición in_progress → cancelled. Registra finished_at.

        Raises:
            PipelineExecutionNotCancellableError: si la ejecución no está en in_progress.
        """
        from app.v1.pipelines.domain.exceptions.pipeline_execution import (
            PipelineExecutionNotCancellableError,
        )

        if self.status.value != "in_progress":
            raise PipelineExecutionNotCancellableError(
                f"No se puede cancelar una ejecución en estado '{self.status.value}'. "
                f"Debe estar en estado 'in_progress'."
            )
        self.status = PipelineStatus("cancelled")
        self.finished_at = datetime.now(timezone.utc)

    def mark_timeout_failed(self) -> None:
        """Transición in_progress → failed tras timeout. Registra finished_at.

        Raises:
            InvalidPipelineStatusError: si la ejecución no está en in_progress.
        """
        if self.status.value != "in_progress":
            raise InvalidPipelineStatusError(
                f"No se puede marcar como failed por timeout una ejecución en estado '{self.status.value}'. "
                f"Debe estar en estado 'in_progress'."
            )
        self.status = PipelineStatus("failed")
        self.finished_at = datetime.now(timezone.utc)

    @staticmethod
    def _calculate_aggregated_status(operation_statuses: list[str]) -> str:
        """RN-20: calcula el estado agregado a partir de los estados de las operaciones.

        - completed: TODAS son 'completed'
        - failed: TODAS son terminales sin ninguna 'completed'
        - partial: al menos una 'completed' y al menos una fallida/cancelada
        """
        has_completed = any(s in _COMPLETED_OPERATION_STATUSES for s in operation_statuses)
        has_failed = any(s in _FAILED_OPERATION_STATUSES for s in operation_statuses)

        if has_completed and has_failed:
            return "partial"
        if has_completed:
            return "completed"
        return "failed"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PipelineExecution):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)