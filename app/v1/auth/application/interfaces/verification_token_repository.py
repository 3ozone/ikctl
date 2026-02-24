"""
Interface para el repositorio de tokens de verificación.

Define el contrato que será implementado en infrastructure/persistence/.
"""
from abc import ABC, abstractmethod
from app.v1.auth.domain.entities import VerificationToken


class VerificationTokenRepository(ABC):
    """Contrato para operaciones de persistencia de tokens de verificación."""

    @abstractmethod
    async def save(self, token: VerificationToken) -> VerificationToken:
        """
        Persiste un token de verificación (email o password reset).

        Args:
            token: Entidad VerificationToken

        Returns:
            VerificationToken persistido

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def find_by_token(self, token: str) -> VerificationToken | None:
        """
        Busca un token de verificación por su valor.

        Args:
            token: Token string

        Returns:
            VerificationToken si existe y no está usado, None si no

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def delete(self, token: str) -> None:
        """
        Elimina un token de verificación (tras usarlo).

        Args:
            token: Token string a eliminar

        Raises:
            InfrastructureException: Error de eliminación
        """

    @abstractmethod
    async def delete_by_user_id(self, user_id: str, token_type: str) -> None:
        """
        Elimina todos los tokens de un tipo para un usuario.

        Útil para invalidar tokens anteriores al generar uno nuevo.

        Args:
            user_id: ID del usuario
            token_type: Tipo de token ('email_verification', 'password_reset')

        Raises:
            InfrastructureException: Error de eliminación
        """
