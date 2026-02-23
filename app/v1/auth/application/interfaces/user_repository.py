"""
Interface para el repositorio de usuarios.

Define el contrato que será implementado en infrastructure/persistence/.
"""
from abc import ABC, abstractmethod
from app.v1.auth.domain.entities import User


class IUserRepository(ABC):
    """Contrato para operaciones de persistencia de usuarios."""

    @abstractmethod
    async def save(self, user: User) -> User:
        """
        Persiste un usuario en el almacenamiento.

        Args:
            user: Entidad User a persistir

        Returns:
            User persistido con id generado

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def find_by_email(self, email: str) -> User | None:
        """
        Busca un usuario por email.

        Args:
            email: Email del usuario

        Returns:
            User si existe, None si no

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def find_by_id(self, user_id: str) -> User | None:
        """
        Busca un usuario por ID.

        Args:
            user_id: ID del usuario

        Returns:
            User si existe, None si no

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def update(self, user: User) -> User:
        """
        Actualiza un usuario existente.

        Args:
            user: Entidad User con cambios

        Returns:
            User actualizado

        Raises:
            ResourceNotFoundError: Usuario no existe
            InfrastructureException: Error de actualización
        """

    @abstractmethod
    async def delete(self, user_id: str) -> None:
        """
        Elimina un usuario (GDPR - derecho al olvido).

        Args:
            user_id: ID del usuario a eliminar

        Raises:
            ResourceNotFoundError: Usuario no existe
            InfrastructureException: Error de eliminación
        """
