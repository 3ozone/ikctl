"""Use Case para activar o desactivar un servidor."""
from datetime import datetime, timezone

from app.v1.servers.application.dtos.server_result import ServerResult
from app.v1.servers.application.interfaces.server_repository import ServerRepository
from app.v1.servers.domain.events.server_status_changed import ServerStatusChanged
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.shared.application.interfaces.event_bus import EventBus


class ToggleServerStatus:
    """Use Case para activar o desactivar un servidor.

    Valida ownership (RN-01) y cambia el estado del servidor.
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
        active: bool,
        correlation_id: str,
    ) -> ServerResult:
        """Activa o desactiva un servidor del usuario.

        Args:
            user_id: ID del usuario propietario
            server_id: ID del servidor a modificar
            active: True para activar, False para desactivar
            correlation_id: ID de trazabilidad del request

        Returns:
            ServerResult con el nuevo estado del servidor

        Raises:
            ServerNotFoundError: Si el servidor no existe o no pertenece al usuario (RN-01)
        """
        server = None
        if self._server_repo is not None:
            server = await self._server_repo.find_by_id(server_id, user_id)

        if server is None:
            raise ServerNotFoundError()

        if active:
            server.activate()
        else:
            server.deactivate()

        server.updated_at = datetime.now(timezone.utc)

        if self._server_repo is not None:
            await self._server_repo.update(server)

        if self._event_bus is not None:
            await self._event_bus.publish(
                ServerStatusChanged(
                    server_id=server.id,
                    user_id=user_id,
                    new_status=server.status.value,
                    correlation_id=correlation_id,
                )
            )

        return ServerResult(
            server_id=server.id,
            user_id=server.user_id,
            name=server.name,
            server_type=server.type.value,
            status=server.status.value,
            host=server.host,
            port=server.port,
            credential_id=server.credential_id,
            description=server.description,
            os_id=server.os_id,
            os_version=server.os_version,
            os_name=server.os_name,
            created_at=server.created_at,
            updated_at=server.updated_at,
        )
