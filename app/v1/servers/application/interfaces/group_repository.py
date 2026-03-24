"""
Interface para el repositorio de grupos de servidores.

Define el contrato que será implementado en infrastructure/persistence/.
"""
from abc import ABC, abstractmethod

from app.v1.servers.domain.entities.group import Group


class GroupRepository(ABC):
    """Contrato para operaciones de persistencia de grupos de servidores."""

    @abstractmethod
    async def save(self, group: Group) -> None:
        """
        Persiste un nuevo grupo.

        Args:
            group: Entidad Group a persistir

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def find_by_id(self, group_id: str, user_id: str) -> Group | None:
        """
        Busca un grupo por id, scoped al usuario propietario.

        Args:
            group_id: ID del grupo
            user_id: ID del usuario propietario

        Returns:
            Group si existe y pertenece al usuario, None si no

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def find_all_by_user(self, user_id: str, page: int, per_page: int) -> list[Group]:
        """
        Lista todos los grupos de un usuario con paginación.

        Args:
            user_id: ID del usuario propietario
            page: Número de página (1-based)
            per_page: Elementos por página (máx 50)

        Returns:
            Lista de Group del usuario

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def update(self, group: Group) -> None:
        """
        Actualiza un grupo existente.

        Args:
            group: Entidad Group con campos actualizados

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def delete(self, group_id: str) -> None:
        """
        Elimina un grupo por id.

        Args:
            group_id: ID del grupo a eliminar

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def has_active_pipeline_executions(self, group_id: str) -> bool:
        """
        Comprueba si el grupo tiene ejecuciones de pipeline activas.

        Usado para proteger el borrado: no se puede eliminar un grupo
        con pipelines en estado pending o running.

        Args:
            group_id: ID del grupo

        Returns:
            True si tiene ejecuciones activas, False si no

        Raises:
            InfrastructureException: Error de consulta
        """
