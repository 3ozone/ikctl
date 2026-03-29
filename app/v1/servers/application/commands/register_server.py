"""Use Case para registrar un nuevo servidor remoto."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.exceptions.credential import CredentialNotFoundError
from app.v1.servers.application.dtos.server_result import ServerResult
from app.v1.servers.application.interfaces.server_repository import ServerRepository
from app.v1.servers.application.interfaces.credential_repository import CredentialRepository
from app.v1.servers.domain.events.server_registered import ServerRegistered
from app.v1.shared.application.interfaces.event_bus import EventBus


class RegisterServer:
    """Use Case para registrar y persistir un nuevo servidor remoto."""

    def __init__(
        self,
        server_repository: ServerRepository | None = None,
        credential_repository: CredentialRepository | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._server_repo = server_repository
        self._credential_repo = credential_repository
        self._event_bus = event_bus

    async def execute(
        self,
        user_id: str,
        name: str,
        host: str,
        port: int,
        credential_id: str,
        description: str | None,
        correlation_id: str,
    ) -> ServerResult:
        """Registra un nuevo servidor remoto.

        Args:
            user_id: ID del usuario propietario
            name: Nombre descriptivo del servidor
            host: Dirección IP o hostname del servidor
            port: Puerto SSH (por defecto 22)
            credential_id: ID de la credencial SSH a usar
            description: Descripción opcional del servidor
            correlation_id: ID de trazabilidad del request

        Returns:
            ServerResult con los datos del servidor creado

        Raises:
            CredentialNotFoundError: Si la credencial no existe o no pertenece al usuario
            InvalidServerConfigurationError: Si la configuración del servidor es inválida
        """
        if self._credential_repo is not None:
            credential = await self._credential_repo.find_by_id(credential_id, user_id)
            if credential is None:
                raise CredentialNotFoundError()

        now = datetime.now(timezone.utc)

        server = Server(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            type=ServerType("remote"),
            status=ServerStatus("active"),
            host=host,
            port=port,
            credential_id=credential_id,
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
                    server_type="remote",
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
