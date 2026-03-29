"""Use Case para listar servidores de un usuario con paginación."""
from app.v1.servers.application.dtos.server_list_result import ServerListResult
from app.v1.servers.application.dtos.server_result import ServerResult
from app.v1.servers.application.interfaces.server_repository import ServerRepository


class ListServers:
    """Use Case para listar servidores de un usuario paginados."""

    def __init__(
        self,
        server_repository: ServerRepository | None = None,
    ) -> None:
        self._server_repo = server_repository

    async def execute(
        self,
        user_id: str,
        page: int,
        per_page: int,
    ) -> ServerListResult:
        """Lista los servidores del usuario con paginación.

        Args:
            user_id: ID del usuario propietario
            page: Número de página (1-based)
            per_page: Elementos por página

        Returns:
            ServerListResult paginado
        """
        servers = []
        if self._server_repo is not None:
            servers = await self._server_repo.find_all_by_user(user_id, page, per_page)

        items = [
            ServerResult(
                server_id=s.id,
                user_id=s.user_id,
                name=s.name,
                server_type=s.type.value,
                status=s.status.value,
                host=s.host,
                port=s.port,
                credential_id=s.credential_id,
                description=s.description,
                os_id=s.os_id,
                os_version=s.os_version,
                os_name=s.os_name,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in servers
        ]

        return ServerListResult(
            items=items,
            total=len(items),
            page=page,
            per_page=per_page,
        )
