"""Use Case para verificar la salud de un servidor via SSH."""
import time

from app.v1.servers.application.dtos.health_check_result import HealthCheckResult
from app.v1.servers.application.interfaces.connection_factory import ConnectionFactory
from app.v1.servers.application.interfaces.server_repository import ServerRepository
from app.v1.servers.domain.exceptions.server import ServerNotFoundError, ServerCredentialRequiredError


class CheckServerHealth:
    """Use Case para verificar la conectividad y SO de un servidor.

    Detecta el SO desde /etc/os-release y actualiza os_info en el servidor.
    Devuelve offline sin lanzar excepción si la conexión falla.
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
    ) -> HealthCheckResult:
        """Verifica la salud del servidor.

        Args:
            user_id: ID del usuario propietario
            server_id: ID del servidor a verificar

        Returns:
            HealthCheckResult con status online/offline, latency_ms y os_info

        Raises:
            ServerNotFoundError: Si el servidor no existe o no pertenece al usuario (RN-01)
        """
        server = None
        if self._server_repo is not None:
            server = await self._server_repo.find_by_id(server_id, user_id)

        if server is None:
            raise ServerNotFoundError()

        if server.credential_id is None:
            raise ServerCredentialRequiredError()

        try:
            if self._connection_factory is None:
                raise ConnectionError("No connection factory provided")
            connection = await self._connection_factory.create(server)
            start = time.monotonic()
            _, stdout, _ = await connection.execute("cat /etc/os-release")
            latency_ms = (time.monotonic() - start) * 1000

            os_id, os_version, os_name = self._parse_os_release(stdout)

            if self._server_repo is not None and os_id is not None and os_version is not None and os_name is not None:
                server.update_os_info(
                    os_id=os_id,
                    os_version=os_version,
                    os_name=os_name,
                )
                await self._server_repo.update(server)

            return HealthCheckResult(
                server_id=server_id,
                status="online",
                latency_ms=round(latency_ms, 2),
                os_id=os_id,
                os_version=os_version,
                os_name=os_name,
            )

        except (ConnectionError, TimeoutError, OSError):
            return HealthCheckResult(
                server_id=server_id,
                status="offline",
                latency_ms=None,
                os_id=None,
                os_version=None,
                os_name=None,
            )

    @staticmethod
    def _parse_os_release(content: str) -> tuple[str | None, str | None, str | None]:
        """Parsea el contenido de /etc/os-release y extrae ID, VERSION_ID y PRETTY_NAME."""
        os_id = None
        os_version = None
        os_name = None
        for line in content.splitlines():
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = value.strip().strip('"')
            if key == "ID":
                os_id = value
            elif key == "VERSION_ID":
                os_version = value
            elif key == "PRETTY_NAME":
                os_name = value
        return os_id, os_version, os_name
