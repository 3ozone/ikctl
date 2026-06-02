"""ServerReadAdapter — Adapter cross-módulo para leer servidores sin ownership.

Implementa el puerto pipelines.application.interfaces.ServerRepository
delegando al SQLAlchemyServerRepository de servers para la conversión
model→entity, y consultando sin filtro de user_id (uso interno de tasks).
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.pipelines.application.interfaces.server_repository import (
    ServerRepository as PipelinesServerRepository,
)
from app.v1.servers.domain.entities.group import Group
from app.v1.servers.domain.entities.server import Server
from app.v1.servers.infrastructure.persistence.models import (
    GroupMemberModel,
    GroupModel,
    ServerModel,
)
from app.v1.servers.infrastructure.repositories.server_repository import (
    SQLAlchemyServerRepository,
)


class ServerReadAdapter(PipelinesServerRepository):
    """Lee servidores y grupos sin filtro de ownership para uso interno de pipelines."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._inner = SQLAlchemyServerRepository(session)

    async def find_server_by_id_internal(self, server_id: str) -> Optional[Server]:
        result = await self._session.execute(
            select(ServerModel).where(ServerModel.id == server_id)
        )
        model = result.scalar_one_or_none()
        return self._inner.model_to_entity(model) if model else None

    async def find_group_by_id_internal(self, group_id: str) -> Optional[Group]:
        result = await self._session.execute(
            select(GroupModel).where(GroupModel.id == group_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        members_result = await self._session.execute(
            select(GroupMemberModel.server_id).where(
                GroupMemberModel.group_id == group_id
            )
        )
        server_ids = list(members_result.scalars().all())
        return Group(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            description=model.description,
            server_ids=server_ids,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def find_servers_by_ids(self, server_ids: list[str]) -> list[Server]:
        if not server_ids:
            return []
        result = await self._session.execute(
            select(ServerModel).where(ServerModel.id.in_(server_ids))
        )
        models = result.scalars().all()
        return [self._inner.model_to_entity(m) for m in models]