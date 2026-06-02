"""
Interface para el repositorio de repositorios Git.

Define el contrato que será implementado en infrastructure/persistence/.
"""
from abc import ABC, abstractmethod

from app.v1.kits.domain.entities.repository import Repository


class RepositoryRepository(ABC):
    """Contrato para operaciones de persistencia de repositorios Git."""

    @abstractmethod
    async def save(self, repository: Repository) -> None:
        """
        Persiste un nuevo repositorio.

        Args:
            repository: Entidad Repository a persistir

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def find_by_id(self, repository_id: str, user_id: str) -> Repository | None:
        """
        Busca un repositorio por id, scoped al usuario propietario.

        Args:
            repository_id: ID del repositorio
            user_id: ID del usuario propietario

        Returns:
            Repository si existe y pertenece al usuario, None si no

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def find_all_by_user(self, user_id: str, page: int, per_page: int) -> list[Repository]:
        """
        Lista todos los repositorios de un usuario con paginación.

        Solo devuelve repositorios con is_deleted=False.

        Args:
            user_id: ID del usuario propietario
            page: Número de página (1-based)
            per_page: Elementos por página (máx 50)

        Returns:
            Lista de Repository del usuario

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def update(self, repository: Repository) -> None:
        """
        Actualiza un repositorio existente.

        Args:
            repository: Entidad Repository con campos actualizados

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def delete(self, repository_id: str) -> None:
        """
        Elimina físicamente un repositorio por id.

        Usado en DeleteRepository tras comprobar que no tiene referencias.

        Args:
            repository_id: ID del repositorio a eliminar

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def has_kits_with_references(self, repository_id: str) -> bool:
        """
        Comprueba si algún kit del repositorio tiene referencias activas
        en pipelines u operaciones.

        Usado para proteger el borrado (RN-30): no se puede eliminar un
        repositorio si sus kits están siendo referenciados.

        Args:
            repository_id: ID del repositorio a comprobar

        Returns:
            True si algún kit tiene referencias activas, False si no

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def find_all_active(self) -> list[Repository]:
        """
        Devuelve todos los repositorios activos (is_deleted=False) de todos
        los usuarios, ordenados por created_at.

        Usado por el scheduler periódico (PeriodicSyncRepositories) para
        sincronizar todos los repositorios registrados en el sistema.

        Returns:
            Lista de Repository activos de todos los usuarios

        Raises:
            InfrastructureException: Error de consulta
        """
