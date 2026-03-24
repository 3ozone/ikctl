"""
Interface para el repositorio de credenciales.

Define el contrato que será implementado en infrastructure/persistence/.
"""
from abc import ABC, abstractmethod

from app.v1.servers.domain.entities.credential import Credential


class CredentialRepository(ABC):
    """Contrato para operaciones de persistencia de credenciales."""

    @abstractmethod
    async def save(self, credential: Credential) -> None:
        """
        Persiste una nueva credencial.

        Args:
            credential: Entidad Credential a persistir

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def find_by_id(self, credential_id: str, user_id: str) -> Credential | None:
        """
        Busca una credencial por id, scoped al usuario propietario.

        Args:
            credential_id: ID de la credencial
            user_id: ID del usuario propietario

        Returns:
            Credential si existe y pertenece al usuario, None si no

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def find_all_by_user(self, user_id: str, page: int, per_page: int) -> list[Credential]:
        """
        Lista todas las credenciales de un usuario con paginación.

        Args:
            user_id: ID del usuario propietario
            page: Número de página (1-based)
            per_page: Elementos por página (máx 50)

        Returns:
            Lista de Credential del usuario

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def update(self, credential: Credential) -> None:
        """
        Actualiza una credencial existente.

        Args:
            credential: Entidad Credential con campos actualizados

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def delete(self, credential_id: str) -> None:
        """
        Elimina una credencial por id.

        Args:
            credential_id: ID de la credencial a eliminar

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def is_used_by_server(self, credential_id: str) -> bool:
        """
        Comprueba si algún servidor activo referencia esta credencial.

        Usado para proteger el borrado: no se puede eliminar una credencial
        si tiene servidores asociados.

        Args:
            credential_id: ID de la credencial

        Returns:
            True si algún servidor la usa, False si no

        Raises:
            InfrastructureException: Error de consulta
        """
