"""Use Case para actualizar un servidor existente."""
from datetime import datetime, timezone

from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.domain.events.server_updated import ServerUpdated
from app.v1.servers.application.dtos.server_result import ServerResult
from app.v1.servers.application.interfaces.server_repository import ServerRepository
from app.v1.shared.application.interfaces.event_bus import EventBus


class UpdateServer:
    """Use Case para actualizar un servidor existente.

    Para servidores remote: permite actualizar name, host, port, credential_id y description.
    Para servidores local: solo permite actualizar name y description (RNF-16).
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
        name: str,
        host: str | None,
        port: int | None,
        credential_id: str | None,
        description: str | None,
        correlation_id: str,
    ) -> ServerResult:
        """Actualiza un servidor existente.

        Args:
            user_id: ID del usuario propietario
            server_id: ID del servidor a actualizar
            name: Nuevo nombre descriptivo
            host: Nuevo host (solo aplica a remote)
            port: Nuevo puerto (solo aplica a remote)
            credential_id: Nueva credencial (solo aplica a remote)
            description: Nueva descripción opcional
            correlation_id: ID de trazabilidad del request

        Returns:
            ServerResult con los datos actualizados

        Raises:
            ServerNotFoundError: Si el servidor no existe o no pertenece al usuario (RN-01)
        """
        server = None
        if self._server_repo is not None:
            server = await self._server_repo.find_by_id(server_id, user_id)

        if server is None:
            raise ServerNotFoundError()

        now = datetime.now(timezone.utc)
        server.update(
            name=name,
            description=description,
            updated_at=now,
            host=host,
            port=port,
            credential_id=credential_id,
        )

        if self._server_repo is not None:
            await self._server_repo.update(server)

        if self._event_bus is not None:
            await self._event_bus.publish(
                ServerUpdated(
                    server_id=server.id,
                    user_id=user_id,
                    name=server.name,
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
