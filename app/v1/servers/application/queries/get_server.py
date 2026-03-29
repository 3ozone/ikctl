"""Use Case para obtener un servidor por su ID."""
from app.v1.servers.application.dtos.server_result import ServerResult
from app.v1.servers.application.interfaces.server_repository import ServerRepository
from app.v1.servers.domain.exceptions.server import ServerNotFoundError


class GetServer:
    """Use Case para obtener un servidor del usuario.

    Valida ownership (RN-01) y devuelve el DTO con credential_id pero sin datos de credencial.
    """

    def __init__(
        self,
        server_repository: ServerRepository | None = None,
    ) -> None:
        self._server_repo = server_repository

    async def execute(
        self,
        user_id: str,
        server_id: str,
    ) -> ServerResult:
        """Obtiene un servidor por su ID.

        Args:
            user_id: ID del usuario propietario
            server_id: ID del servidor a obtener

        Returns:
            ServerResult con credential_id pero sin datos de la credencial

        Raises:
            ServerNotFoundError: Si el servidor no existe o no pertenece al usuario (RN-01)
        """
        server = None
        if self._server_repo is not None:
            server = await self._server_repo.find_by_id(server_id, user_id)

        if server is None:
            raise ServerNotFoundError()

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
