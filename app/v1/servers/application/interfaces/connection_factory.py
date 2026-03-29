"""
Interface para la factoría de conexiones a servidores.

Define el contrato que será implementado en infrastructure/adapters/.
Selecciona SSHConnectionAdapter o LocalConnectionAdapter según server.type.
"""
from abc import ABC, abstractmethod

from app.v1.servers.application.interfaces.connection import Connection
from app.v1.servers.domain.entities.server import Server


class ConnectionFactory(ABC):
    """Contrato para crear conexiones a servidores según su tipo."""

    @abstractmethod
    async def create(self, server: Server) -> Connection:
        """
        Crea y devuelve una conexión al servidor indicado.

        Para servidores remote devuelve un SSHConnectionAdapter.
        Para servidores local devuelve un LocalConnectionAdapter.

        Args:
            server: Entidad Server con los datos de conexión

        Returns:
            Connection lista para ejecutar comandos

        Raises:
            ConnectionError: Si no se puede establecer la conexión
        """
