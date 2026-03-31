"""ConnectionFactory — Selecciona el adaptador de conexión según el tipo de servidor.

Para servidores `remote`: crea un SSHConnectionAdapter resolviendo la credencial
del CredentialRepository. La credencial se descifra en memoria y nunca se persiste
en claro.

Para servidores `local`: devuelve un LocalConnectionAdapter sin consultar credenciales.
"""
from app.v1.servers.application.interfaces.connection import Connection
from app.v1.servers.application.interfaces.connection_factory import ConnectionFactory as ConnectionFactoryPort
from app.v1.servers.application.interfaces.credential_repository import CredentialRepository
from app.v1.servers.domain.entities.server import Server
from app.v1.servers.infrastructure.adapters.local_connection import LocalConnectionAdapter
from app.v1.servers.infrastructure.adapters.ssh_connection import SSHConnectionAdapter


class ConnectionFactory(ConnectionFactoryPort):
    """Factory que construye el adaptador de conexión adecuado para un servidor."""

    def __init__(self, credential_repository: CredentialRepository) -> None:
        self._credential_repo = credential_repository

    async def create(self, server: Server) -> Connection:
        """Crea y devuelve el adaptador de conexión para el servidor dado.

        Args:
            server: Entidad Server para la que se crea la conexión.

        Returns:
            SSHConnectionAdapter para servidores remote.
            LocalConnectionAdapter para servidores local.

        Raises:
            ValueError: Si el servidor remote referencia una credencial inexistente.
        """
        if server.type.value == "local":
            return LocalConnectionAdapter()

        # Servidor remote — resolver credencial
        # server.credential_id está garantizado por Server.__post_init__ para type=remote
        credential_id: str = server.credential_id  # type: ignore[assignment]
        credential = await self._credential_repo.find_by_id(
            credential_id, server.user_id
        )
        if credential is None:
            raise ValueError(
                f"Credencial '{server.credential_id}' no encontrada para el servidor '{server.id}'"
            )

        return SSHConnectionAdapter(
            host=server.host,  # type: ignore[arg-type]
            port=server.port or 22,
            username=credential.username,  # type: ignore[arg-type]
            private_key=credential.private_key,
            password=credential.password,
        )
