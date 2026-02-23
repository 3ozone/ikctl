"""
Interface para el repositorio de refresh tokens.

Define el contrato que será implementado en infrastructure/persistence/.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from app.v1.auth.domain.entities import RefreshToken


class IRefreshTokenRepository(ABC):
    """Contrato para operaciones de persistencia de refresh tokens."""

    @abstractmethod
    async def save(self, token: RefreshToken) -> RefreshToken:
        """
        Persiste un refresh token.

        Args:
            token: Entidad RefreshToken

        Returns:
            RefreshToken persistido

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def find_by_token(self, token: str) -> Optional[RefreshToken]:
        """
        Busca un refresh token por su valor.

        Args:
            token: Token JWT string

        Returns:
            RefreshToken si existe y no está revocado, None si no

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def delete(self, token: str) -> None:
        """
        Elimina (revoca) un refresh token.

        Args:
            token: Token JWT string a revocar

        Raises:
            InfrastructureException: Error de eliminación
        """

    @abstractmethod
    async def delete_by_user_id(self, user_id: str) -> None:
        """
        Elimina todos los refresh tokens de un usuario (logout global).

        Args:
            user_id: ID del usuario

        Raises:
            InfrastructureException: Error de eliminación
        """

    @abstractmethod
    async def count_by_user_id(self, user_id: str) -> int:
        """
        Cuenta los tokens activos de un usuario (para validar límite de sesiones).

        Args:
            user_id: ID del usuario

        Returns:
            Número de tokens activos (no expirados, no revocados)

        Raises:
            InfrastructureException: Error de consulta
        """

    @abstractmethod
    async def find_by_user_id(self, user_id: str) -> List[RefreshToken]:
        """
        Obtiene todos los refresh tokens activos de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Lista de RefreshToken activos

        Raises:
            InfrastructureException: Error de consulta
        """
