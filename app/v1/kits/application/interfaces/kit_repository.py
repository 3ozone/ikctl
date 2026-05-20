"""
Interface para el repositorio de kits.

Define el contrato que será implementado en infrastructure/persistence/.
"""
from abc import ABC, abstractmethod

from app.v1.kits.domain.entities.kit import Kit


class KitRepository(ABC):
    """Contrato para operaciones de persistencia de kits."""

    @abstractmethod
    async def save(self, kit: Kit) -> None:
        """
        Persiste un nuevo kit.

        Args:
            kit: Entidad Kit a persistir

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def find_by_id(self, kit_id: str, user_id: str) -> Kit | None:
        """
        Busca un kit por id, scoped al usuario propietario.

        Solo devuelve kits con is_deleted=False.

        Args:
            kit_id: ID del kit
            user_id: ID del usuario propietario

        Returns:
            Kit si existe, pertenece al usuario y no está eliminado, None si no

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def find_by_id_internal(self, kit_id: str) -> Kit | None:
        """
        Busca un kit por id sin filtro de usuario ni is_deleted.

        Usado internamente por use cases que necesitan acceder a kits
        eliminados o de cualquier usuario (ej: comprobación de referencias).

        Args:
            kit_id: ID del kit

        Returns:
            Kit si existe, None si no

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def find_by_repository_id(self, repository_id: str) -> list[Kit]:
        """
        Lista todos los kits de un repositorio, incluyendo eliminados.

        Usado en SyncRepository para reconciliar el estado de kits
        entre la DB y el repositorio Git.

        Args:
            repository_id: ID del repositorio fuente

        Returns:
            Lista de todos los Kit del repositorio (incluye is_deleted=True)

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def find_all_by_user(
        self,
        user_id: str,
        page: int,
        per_page: int,
        tags_filter: list[str] | None = None,
        repository_id_filter: str | None = None,
    ) -> list[Kit]:
        """
        Lista kits de un usuario con paginación y filtros opcionales.

        Solo devuelve kits con is_deleted=False.

        Args:
            user_id: ID del usuario propietario
            page: Número de página (1-based)
            per_page: Elementos por página (máx 50)
            tags_filter: Lista de tags para filtrar (AND semántico), None = sin filtro
            repository_id_filter: ID de repositorio para filtrar, None = sin filtro

        Returns:
            Lista de Kit del usuario que cumplen los filtros

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def update(self, kit: Kit) -> None:
        """
        Actualiza un kit existente.

        Args:
            kit: Entidad Kit con campos actualizados

        Raises:
            InfrastructureException: Error de persistencia
        """
