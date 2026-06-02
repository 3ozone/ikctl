"""KitReadAdapter — Adapter cross-módulo para leer kits sin ownership.

Implementa el puerto operations.application.interfaces.KitRepository
delegando a SQLAlchemyKitRepository.find_by_id_internal.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.kits.domain.entities.kit import Kit
from app.v1.kits.infrastructure.repositories.kit_repository import SQLAlchemyKitRepository
from app.v1.operations.application.interfaces.kit_repository import (
    KitRepository as OperationsKitRepository,
)


class KitReadAdapter(OperationsKitRepository):
    """Lee kits sin filtro de ownership para uso interno de tasks/use cases."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = SQLAlchemyKitRepository(session)

    async def find_by_id_internal(self, kit_id: str) -> Optional[Kit]:
        """Busca un kit por id sin validar ownership (incluye eliminados)."""
        return await self._repo.find_by_id_internal(kit_id)
