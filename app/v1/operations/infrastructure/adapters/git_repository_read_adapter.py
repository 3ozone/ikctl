"""GitRepositoryReadAdapter — Adapter cross-módulo para leer repositorios git sin ownership.

Implementa el puerto operations.application.interfaces.GitRepositoryPort
delegando a SQLAlchemyRepositoryRepository.find_by_id_internal.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.kits.domain.entities.repository import Repository
from app.v1.kits.infrastructure.repositories.repository_repository import (
    SQLAlchemyRepositoryRepository,
)
from app.v1.operations.application.interfaces.git_repository_port import GitRepositoryPort


class GitRepositoryReadAdapter(GitRepositoryPort):
    """Lee repositorios git sin filtro de ownership para uso interno de tasks."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = SQLAlchemyRepositoryRepository(session)

    async def find_by_id_internal(self, repository_id: str) -> Optional[Repository]:
        """Busca un repositorio por id sin validar ownership."""
        return await self._repo.find_by_id_internal(repository_id)
