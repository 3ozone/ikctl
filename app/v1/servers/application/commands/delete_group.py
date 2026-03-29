"""Use Case para eliminar un grupo de servidores."""
from app.v1.servers.application.exceptions import GroupInUseError
from app.v1.servers.application.interfaces.group_repository import GroupRepository
from app.v1.servers.domain.events.group_deleted import GroupDeleted
from app.v1.servers.domain.exceptions.group import GroupNotFoundError
from app.v1.shared.application.interfaces.event_bus import EventBus


class DeleteGroup:
    """Use Case para eliminar un grupo de servidores.

    Valida ownership (RN-01) y que no tenga pipelines activos (RN-19).
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
        correlation_id: str,
    ) -> None:
        """Elimina un grupo de servidores del usuario.

        Args:
            user_id: ID del usuario propietario
            group_id: ID del grupo a eliminar
            correlation_id: ID de trazabilidad del request

        Raises:
            GroupNotFoundError: Si el grupo no existe o no pertenece al usuario (RN-01)
            GroupInUseError: Si el grupo tiene pipelines activos (RN-19)
        """
        if self._group_repo is None:
            raise GroupNotFoundError()

        group = await self._group_repo.find_by_id(group_id, user_id)
        if group is None:
            raise GroupNotFoundError()

        has_active = await self._group_repo.has_active_pipeline_executions(group_id)
        if has_active:
            raise GroupInUseError()

        await self._group_repo.delete(group_id)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GroupDeleted(
                    group_id=group_id,
                    user_id=user_id,
                    correlation_id=correlation_id,
                )
            )
