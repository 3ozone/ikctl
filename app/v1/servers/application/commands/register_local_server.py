"""Use Case para registrar un nuevo servidor local."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.application.dtos.server_result import ServerResult
from app.v1.servers.application.interfaces.server_repository import ServerRepository
from app.v1.servers.application.exceptions import DuplicateLocalServerError, UnauthorizedOperationError
from app.v1.servers.domain.events.server_registered import ServerRegistered
from app.v1.shared.application.interfaces.event_bus import EventBus


class RegisterLocalServer:
    """Use Case para registrar y persistir un nuevo servidor local.

    Solo puede haber un servidor local por usuario (RN-07).
    Solo usuarios con rol admin pueden crear servidores locales (RNF-16).
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
        user_role: str,
        name: str,
        description: str | None,
        correlation_id: str,
    ) -> ServerResult:
        """Registra un nuevo servidor local.

        Args:
            user_id: ID del usuario propietario
            user_role: Rol del usuario ("admin" o "user")
            name: Nombre descriptivo del servidor
            description: Descripción opcional del servidor
            correlation_id: ID de trazabilidad del request

        Returns:
            ServerResult con los datos del servidor creado

        Raises:
            UnauthorizedOperationError: Si el usuario no tiene rol admin (RNF-16)
            DuplicateLocalServerError: Si ya existe un servidor local para el usuario (RN-07)
        """
        if user_role != "admin":
            raise UnauthorizedOperationError()

        if self._server_repo is not None:
            existing = await self._server_repo.find_local_by_user(user_id)
            if existing:
                raise DuplicateLocalServerError()

        now = datetime.now(timezone.utc)

        server = Server(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            type=ServerType("local"),
            status=ServerStatus("active"),
            host=None,
            port=None,
            credential_id=None,
            description=description,
            os_id=None,
            os_version=None,
            os_name=None,
            created_at=now,
            updated_at=now,
        )

        if self._server_repo is not None:
            await self._server_repo.save(server)

        if self._event_bus is not None:
            await self._event_bus.publish(
                ServerRegistered(
                    server_id=server.id,
                    user_id=user_id,
                    name=name,
                    server_type="local",
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
