"""Port OperationRepository — T-04."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.v1.operations.domain.entities.operation import Operation


class OperationRepository(ABC):
    """Contrato de persistencia para la entity Operation."""

    @abstractmethod
    async def save(self, operation: Operation) -> None:
        """Persiste una nueva operación."""

    @abstractmethod
    async def find_by_id(self, operation_id: str, user_id: str) -> Optional[Operation]:
        """Devuelve la operación si existe y pertenece al usuario, None en caso contrario."""

    @abstractmethod
    async def find_all_by_user(
        self,
        user_id: str,
        page: int,
        per_page: int,
        server_id: Optional[str] = None,
        kit_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> tuple[list[Operation], int]:
        """Lista las operaciones del usuario con paginación y filtros opcionales.

        Returns:
            Tupla (lista de operaciones, total de resultados).
        """

    @abstractmethod
    async def update(self, operation: Operation) -> None:
        """Persiste los cambios sobre una operación existente."""

    @abstractmethod
    async def find_by_id_no_ownership(self, operation_id: str) -> Optional[Operation]:
        """Devuelve la operación por id sin validar ownership (uso interno de tasks)."""
