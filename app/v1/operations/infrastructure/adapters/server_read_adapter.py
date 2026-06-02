"""ServerReadAdapter — Adapter cross-módulo para leer servidores sin ownership.

Implementa el puerto operations.application.interfaces.ServerRepository
delegando al SQLAlchemyServerRepository de servers para la conversión
model→entity, y consultando sin filtro de user_id (uso interno de tasks).
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.operations.application.interfaces.server_repository import (
    ServerRepository as OperationsServerRepository,
)
from app.v1.servers.domain.entities.server import Server
from app.v1.servers.infrastructure.repositories.server_repository import (
    SQLAlchemyServerRepository,
)
from app.v1.servers.infrastructure.persistence.models import ServerModel


class ServerReadAdapter(OperationsServerRepository):
    """Lee servidores sin filtro de ownership para uso interno de tasks/use cases.

    Delega la conversión model→entity al SQLAlchemyServerRepository para
    evitar duplicación de lógica de mapeo.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._inner = SQLAlchemyServerRepository(session)

    async def find_by_id_internal(self, server_id: str) -> Optional[Server]:
        """Busca un servidor por id sin validar ownership."""
        result = await self._session.execute(
            select(ServerModel).where(ServerModel.id == server_id)
        )
        model = result.scalar_one_or_none()
        return self._inner.model_to_entity(model) if model else None