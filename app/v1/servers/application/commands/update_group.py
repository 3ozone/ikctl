"""Use Case para actualizar un grupo de servidores."""
from datetime import datetime, timezone

from app.v1.servers.application.dtos.group_result import GroupResult
from app.v1.servers.application.interfaces.group_repository import GroupRepository
from app.v1.servers.domain.events.group_updated import GroupUpdated
from app.v1.servers.domain.exceptions.group import GroupNotFoundError
from app.v1.shared.application.interfaces.event_bus import EventBus


class UpdateGroup:
    """Use Case para actualizar un grupo de servidores.

    Valida ownership (RN-01) y actualiza los campos mutables del grupo.
    """

    def __init__(
        self,
        group_repository: GroupRepository | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._group_repo = group_repository
        self._event_bus = event_bus

    async def execute(
        self,
        user_id: str,
        group_id: str,
        name: str,
        description: str | None,
        server_ids: list[str],
        correlation_id: str,
    ) -> GroupResult:
        """Actualiza un grupo de servidores existente.

        Args:
            user_id: ID del usuario propietario
            group_id: ID del grupo a actualizar
            name: Nuevo nombre descriptivo
            description: Nueva descripción opcional
            server_ids: Nueva lista de IDs de servidores
            correlation_id: ID de trazabilidad del request

        Returns:
            GroupResult con los datos actualizados

        Raises:
            GroupNotFoundError: Si el grupo no existe o no pertenece al usuario (RN-01)
        """
        group = None
        if self._group_repo is not None:
            group = await self._group_repo.find_by_id(group_id, user_id)

        if group is None:
            raise GroupNotFoundError()

        now = datetime.now(timezone.utc)
        group.update(
            name=name,
            description=description,
            server_ids=server_ids,
            updated_at=now,
        )

        if self._group_repo is not None:
            await self._group_repo.update(group)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GroupUpdated(
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
