"""
Interface para el proveedor de OAuth con GitHub.

Define el contrato que será implementado en infrastructure/adapters/.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class IGitHubOAuth(ABC):
    """Contrato para autenticación OAuth2 con GitHub."""

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """
        Genera URL de autorización de GitHub.

        Args:
            state: Estado único para prevenir CSRF

        Returns:
            URL completa para redirigir al usuario

        Raises:
            InfrastructureException: Error al generar URL
        """

    @abstractmethod
    async def exchange_code_for_token(self, code: str) -> str:
        """
        Intercambia authorization code por access token de GitHub.

        Args:
            code: Authorization code recibido en callback

        Returns:
            Access token de GitHub

        Raises:
            InvalidTokenError: Code inválido o expirado
            InfrastructureException: Error en petición HTTP
        """

    @abstractmethod
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Obtiene información del usuario desde GitHub API.

        Args:
            access_token: Access token de GitHub

        Returns:
            Dict con: id, email, name, avatar_url

        Raises:
            InvalidTokenError: Token inválido
            InfrastructureException: Error en petición HTTP
        """
