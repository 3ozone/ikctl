"""OperationReadAdapter — Adapter cross-módulo para leer operaciones sin ownership.

Implementa el puerto pipelines.application.interfaces.OperationRepository
delegando al SQLAlchemyOperationRepository de operations.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.operations.application.interfaces.operation_repository import (
    OperationRepository as OperationsOperationRepository,
)
from app.v1.operations.domain.entities.operation import Operation
from app.v1.operations.infrastructure.repositories.operation_repository import (
    SQLAlchemyOperationRepository,
)


class OperationReadAdapter(OperationsOperationRepository):
    """Lee operaciones sin filtro de ownership para uso interno de pipelines."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = SQLAlchemyOperationRepository(session)

    async def find_by_id_no_ownership(self, operation_id: str) -> Optional[Operation]:
        return await self._repo.find_by_id_no_ownership(operation_id)

    async def find_by_id_internal(self, operation_id: str) -> Optional[Operation]:
        return await self._repo.find_by_id_no_ownership(operation_id)

    async def save(self, operation: Operation) -> None:
        raise NotImplementedError("OperationReadAdapter es de solo lectura")

    async def update(self, operation: Operation) -> None:
        raise NotImplementedError("OperationReadAdapter es de solo lectura")

    async def find_by_id(self, operation_id: str, user_id: str) -> Optional[Operation]:
        raise NotImplementedError("OperationReadAdapter es de solo lectura")

    async def find_all_by_user(
        self,
        user_id: str,
        page: int,
        per_page: int,
        server_id: Optional[str] = None,
        kit_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> tuple[list[Operation], int]:
        raise NotImplementedError("OperationReadAdapter es de solo lectura")