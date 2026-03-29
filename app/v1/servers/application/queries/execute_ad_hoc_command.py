"""Use Case para ejecutar un comando ad-hoc en un servidor."""
from app.v1.servers.application.dtos.ad_hoc_command_result import AdHocCommandResult
from app.v1.servers.application.interfaces.connection_factory import ConnectionFactory
from app.v1.servers.application.interfaces.server_repository import ServerRepository
from app.v1.servers.domain.exceptions.server import ServerNotFoundError


class ExecuteAdHocCommand:
    """Use Case para ejecutar un comando puntual en un servidor.

    Valida ownership (RN-01) y devuelve stdout, stderr y exit_code.
    """

    def __init__(
        self,
        server_repository: ServerRepository | None = None,
        connection_factory: ConnectionFactory | None = None,
    ) -> None:
        self._server_repo = server_repository
        self._connection_factory = connection_factory

    async def execute(
        self,
        user_id: str,
        server_id: str,
        command: str,
    ) -> AdHocCommandResult:
        """Ejecuta un comando en el servidor indicado.

        Args:
            user_id: ID del usuario propietario
            server_id: ID del servidor donde ejecutar el comando
            command: Comando a ejecutar

        Returns:
            AdHocCommandResult con stdout, stderr y exit_code

        Raises:
            ServerNotFoundError: Si el servidor no existe o no pertenece al usuario (RN-01)
        """
        server = None
        if self._server_repo is not None:
            server = await self._server_repo.find_by_id(server_id, user_id)

        if server is None:
            raise ServerNotFoundError()

        if self._connection_factory is None:
            raise ServerNotFoundError()

        connection = await self._connection_factory.create(server)
        exit_code, stdout, stderr = await connection.execute(command)

        return AdHocCommandResult(
            server_id=server_id,
            command=command,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
        )
