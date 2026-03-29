"""Use Case para eliminar un servidor."""
from app.v1.servers.application.interfaces.server_repository import ServerRepository
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.application.exceptions import ServerInUseError
from app.v1.servers.domain.events.server_deleted import ServerDeleted
from app.v1.shared.application.interfaces.event_bus import EventBus


class DeleteServer:
    """Use Case para eliminar un servidor.

    Valida ownership (RN-01) y que no tenga operaciones activas (RN-08).
    """

    def __init__(
        self,
        server_repository: ServerRepository | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._server_repo = server_repository
        self._event_bus = event_bus

    async def execute(
        self,
        user_id: str,
        server_id: str,
        correlation_id: str,
    ) -> None:
        """Elimina un servidor del usuario.

        Args:
            user_id: ID del usuario propietario
            server_id: ID del servidor a eliminar
            correlation_id: ID de trazabilidad del request

        Raises:
            ServerNotFoundError: Si el servidor no existe o no pertenece al usuario (RN-01)
            ServerInUseError: Si el servidor tiene operaciones activas (RN-08)
        """
        if self._server_repo is None:
            raise ServerNotFoundError()

        server = await self._server_repo.find_by_id(server_id, user_id)
        if server is None:
            raise ServerNotFoundError()

        has_active = await self._server_repo.has_active_operations(server_id)
        if has_active:
            raise ServerInUseError()

        await self._server_repo.delete(server_id)

        if self._event_bus is not None:
            await self._event_bus.publish(
                ServerDeleted(
                    server_id=server_id,
                    user_id=user_id,
                    correlation_id=correlation_id,
                )
            )
