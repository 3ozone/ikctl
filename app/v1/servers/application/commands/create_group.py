"""Use Case para crear un grupo de servidores."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.servers.application.dtos.group_result import GroupResult
from app.v1.servers.application.exceptions import LocalServerNotAllowedInGroupError
from app.v1.servers.application.interfaces.group_repository import GroupRepository
from app.v1.servers.application.interfaces.server_repository import ServerRepository
from app.v1.servers.domain.entities.group import Group
from app.v1.servers.domain.events.group_created import GroupCreated
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.shared.application.interfaces.event_bus import EventBus


class CreateGroup:
    """Use Case para crear un grupo de servidores.

    Valida que todos los server_ids pertenecen al usuario (RN-01) y que
    ninguno es de tipo local (RNF-16).
    """

    def __init__(
        self,
        group_repository: GroupRepository | None = None,
        server_repository: ServerRepository | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._group_repo = group_repository
        self._server_repo = server_repository
        self._event_bus = event_bus

    async def execute(
        self,
        user_id: str,
        name: str,
        description: str | None,
        server_ids: list[str],
        correlation_id: str,
    ) -> GroupResult:
        """Crea un nuevo grupo de servidores.

        Args:
            user_id: ID del usuario propietario
            name: Nombre descriptivo del grupo
            description: Descripción opcional del grupo
            server_ids: Lista de IDs de servidores a incluir en el grupo
            correlation_id: ID de trazabilidad del request

        Returns:
            GroupResult con los datos del grupo creado

        Raises:
            ServerNotFoundError: Si algún server_id no existe o no pertenece al usuario (RN-01)
            LocalServerNotAllowedInGroupError: Si algún server_id es de tipo local (RNF-16)
        """
        for server_id in server_ids:
            if self._server_repo is not None:
                server = await self._server_repo.find_by_id(server_id, user_id)
                if server is None:
                    raise ServerNotFoundError()
                if server.type.value == "local":
                    raise LocalServerNotAllowedInGroupError()

        now = datetime.now(timezone.utc)
        group = Group(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            server_ids=list(server_ids),
            created_at=now,
            updated_at=now,
        )

        if self._group_repo is not None:
            await self._group_repo.save(group)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GroupCreated(
                    group_id=group.id,
                    user_id=user_id,
                    name=group.name,
                    correlation_id=correlation_id,
                )
            )

        return GroupResult(
            group_id=group.id,
            user_id=group.user_id,
            name=group.name,
            description=group.description,
            server_ids=group.server_ids,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )
