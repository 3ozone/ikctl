"""
Interface para el proveedor de JWT tokens.

Define el contrato que será implementado en infrastructure/adapters/.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from app.v1.auth.domain.value_objects import JWTToken


class IJWTProvider(ABC):
    """Contrato para operaciones de generación y validación de JWT."""

    @abstractmethod
    def create_access_token(self, user_id: str, additional_claims: Dict[str, Any] | None = None) -> JWTToken:
        """
        Genera un JWT access token.

        Args:
            user_id: ID del usuario
            additional_claims: Claims adicionales opcionales

        Returns:
            JWTToken con access token (exp: 30 min)

        Raises:
            InfrastructureException: Error al generar token
        """

    @abstractmethod
    def create_refresh_token(self, user_id: str) -> JWTToken:
        """
        Genera un JWT refresh token.

        Args:
            user_id: ID del usuario

        Returns:
            JWTToken con refresh token (exp: 7 días)

        Raises:
            InfrastructureException: Error al generar token
        """

    @abstractmethod
    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decodifica y valida un JWT token.

        Args:
            token: Token JWT string

        Returns:
            Payload del token (claims)

        Raises:
            InvalidTokenError: Token inválido o malformado
            TokenExpiredError: Token expirado
        """

    @abstractmethod
    def verify_token(self, token: str) -> bool:
        """
        Verifica si un token es válido y no ha expirado.

        Args:
            token: Token JWT string

        Returns:
            True si válido, False si no

        Raises:
            InfrastructureException: Error al verificar
        """
