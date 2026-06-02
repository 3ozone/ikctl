"""Port OperationRepository (cross-module, read-only) — T-09.2.

Port propio del módulo pipelines para consultar el estado de operaciones
individuales durante el polling de _ExecutePipelineOperations.
El adapter en main.py delega al SQLAlchemyOperationRepository del módulo operations.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.v1.operations.domain.entities.operation import Operation


class OperationRepository(ABC):
    """Contrato de solo lectura sobre operaciones (uso interno de tasks)."""

    @abstractmethod
    async def find_by_id_internal(self, operation_id: str) -> Optional[Operation]:
        """Devuelve la operación por id sin validar ownership, o None si no existe."""
