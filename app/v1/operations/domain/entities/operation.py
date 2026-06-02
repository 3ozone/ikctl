"""Entity Operation — ciclo de vida de una operación SSH/local."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.v1.operations.domain.value_objects.operation_status import OperationStatus
from app.v1.operations.domain.exceptions.operation import InvalidOperationTransitionError


@dataclass
class Operation:
    """Representa una operación de ejecución de un kit sobre un servidor.

    La entity encapsula la state machine de 6 estados:
        pending → in_progress → completed
                              → failed
        pending →             → cancelled        (limpia)
                in_progress   → cancelled_unsafe  (servidor puede quedar parcial)

    Invariantes:
        - Los estados terminales no pueden cambiar.
        - start() solo válido desde pending.
        - complete()/fail()/cancel_unsafe() solo válidos desde in_progress.
        - cancel() solo válido desde pending.
    """

    id: str
    user_id: str
    server_id: str
    kit_id: str
    values: dict
    sudo: bool
    status: OperationStatus
    debug_level: str
    output: str
    backup_files: tuple
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    # -------------------------------------------------------------------
    # Comandos de negocio
    # -------------------------------------------------------------------

    def start(self, started_at: datetime) -> None:
        """Transición pending → in_progress."""
        if self.status != OperationStatus("pending"):
            raise InvalidOperationTransitionError(
                f"No se puede iniciar una operación en estado '{self.status.value}'. "
                "Solo es posible desde 'pending'."
            )
        self.status = OperationStatus("in_progress")
        self.started_at = started_at
        self.updated_at = started_at

    def complete(self, finished_at: datetime) -> None:
        """Transición in_progress → completed."""
        if self.status != OperationStatus("in_progress"):
            raise InvalidOperationTransitionError(
                f"No se puede completar una operación en estado '{self.status.value}'. "
                "Solo es posible desde 'in_progress'."
            )
        self.status = OperationStatus("completed")
        self.finished_at = finished_at
        self.updated_at = finished_at

    def fail(self, finished_at: datetime) -> None:
        """Transición in_progress → failed."""
        if self.status != OperationStatus("in_progress"):
            raise InvalidOperationTransitionError(
                f"No se puede marcar como fallida una operación en estado '{self.status.value}'. "
                "Solo es posible desde 'in_progress'."
            )
        self.status = OperationStatus("failed")
        self.finished_at = finished_at
        self.updated_at = finished_at

    def cancel(self, finished_at: datetime) -> None:
        """Transición pending → cancelled (cancelación limpia)."""
        if self.status != OperationStatus("pending"):
            raise InvalidOperationTransitionError(
                f"No se puede cancelar limpiamente una operación en estado '{self.status.value}'. "
                "Solo es posible desde 'pending'. "
                "Para cancelar desde 'in_progress' usa cancel_unsafe()."
            )
        self.status = OperationStatus("cancelled")
        self.finished_at = finished_at
        self.updated_at = finished_at

    def cancel_unsafe(self, finished_at: datetime) -> None:
        """Transición in_progress → cancelled_unsafe (servidor puede quedar en estado parcial)."""
        if self.status != OperationStatus("in_progress"):
            raise InvalidOperationTransitionError(
                f"No se puede cancelar (unsafe) una operación en estado '{self.status.value}'. "
                "Solo es posible desde 'in_progress'."
            )
        self.status = OperationStatus("cancelled_unsafe")
        self.finished_at = finished_at
        self.updated_at = finished_at

    def append_output(self, text: str) -> None:
        """Acumula texto de salida de la operación."""
        self.output = self.output + text

    def set_backup_files(self, files: tuple[str, ...]) -> None:
        """Establece los ficheros de backup tras el snapshot (paso 1).

        Solo debe llamarse durante la ejecución (in_progress).
        """
        self.backup_files = files

    # -------------------------------------------------------------------
    # Queries de estado
    # -------------------------------------------------------------------

    def is_terminal(self) -> bool:
        """True si el estado es terminal (no cambiará)."""
        return self.status.is_terminal()

    def is_retriable(self) -> bool:
        """True si la operación puede reintentarse (failed o cancelled_unsafe)."""
        return self.status.is_retriable()

    def is_restorable(self) -> bool:
        """True si se puede restaurar el backup.

        Condiciones: estado failed o cancelled_unsafe, Y backup_files no vacío.
        """
        return self.status.is_retriable() and len(self.backup_files) > 0

    # -------------------------------------------------------------------
    # Identidad
    # -------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Operation):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
