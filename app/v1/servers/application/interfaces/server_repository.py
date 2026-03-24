"""
Interface para el repositorio de servidores.

Define el contrato que será implementado en infrastructure/persistence/.
"""
from abc import ABC, abstractmethod

from app.v1.servers.domain.entities.server import Server


class ServerRepository(ABC):
    """Contrato para operaciones de persistencia de servidores."""

    @abstractmethod
    async def save(self, server: Server) -> None:
        """
        Persiste un nuevo servidor.

        Args:
            server: Entidad Server a persistir

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def find_by_id(self, server_id: str, user_id: str) -> Server | None:
        """
        Busca un servidor por id, scoped al usuario propietario.

        Args:
            server_id: ID del servidor
            user_id: ID del usuario propietario

        Returns:
            Server si existe y pertenece al usuario, None si no

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def find_all_by_user(self, user_id: str, page: int, per_page: int) -> list[Server]:
        """
        Lista todos los servidores de un usuario con paginación.

        Args:
            user_id: ID del usuario propietario
            page: Número de página (1-based)
            per_page: Elementos por página (máx 50)

        Returns:
            Lista de Server del usuario

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def update(self, server: Server) -> None:
        """
        Actualiza un servidor existente.

        Args:
            server: Entidad Server con campos actualizados

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def delete(self, server_id: str) -> None:
        """
        Elimina un servidor por id.

        Args:
            server_id: ID del servidor a eliminar

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def find_local_by_user(self, user_id: str) -> list[Server]:
        """
        Lista todos los servidores locales de un usuario.

        Usado para validar que no se añaden servidores locales a grupos
        (RNF-16: los grupos solo admiten servidores remotos).

        Args:
            user_id: ID del usuario propietario

        Returns:
            Lista de Server de tipo local

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def has_active_operations(self, server_id: str) -> bool:
        """
        Comprueba si el servidor tiene operaciones en curso.

        Usado para proteger el borrado: no se puede eliminar un servidor
        con operaciones activas (estado pending o running).

        Args:
            server_id: ID del servidor

        Returns:
            True si tiene operaciones activas, False si no

        Raises:
            InfrastructureException: Error de consulta
        """
