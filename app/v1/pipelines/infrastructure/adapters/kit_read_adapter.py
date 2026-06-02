"""KitReadAdapter — Adapter cross-módulo para leer kits sin ownership.

Implementa el puerto pipelines.application.interfaces.KitRepository
delegando a SQLAlchemyKitRepository.find_by_id_internal.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.kits.domain.entities.kit import Kit
from app.v1.kits.infrastructure.repositories.kit_repository import SQLAlchemyKitRepository
from app.v1.pipelines.application.interfaces.kit_repository import (
    KitRepository as PipelinesKitRepository,
)


class KitReadAdapter(PipelinesKitRepository):
    """Lee kits sin filtro de ownership para uso interno de pipelines."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = SQLAlchemyKitRepository(session)

    async def find_by_id_internal(self, kit_id: str) -> Optional[Kit]:
        return await self._repo.find_by_id_internal(kit_id)