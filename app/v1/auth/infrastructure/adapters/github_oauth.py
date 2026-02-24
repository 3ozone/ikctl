"""HttpxGitHubOAuth - Implementación de GitHubOAuth usando httpx.

Adapter para autenticación OAuth2 con GitHub usando httpx async HTTP client.
"""
from typing import Dict, Any
from urllib.parse import urlencode
import httpx

from app.v1.auth.application.interfaces.github_oauth import GitHubOAuth
from app.v1.auth.application.exceptions import InvalidTokenError
from app.v1.auth.infrastructure.exceptions import InfrastructureException


class HttpxGitHubOAuth(GitHubOAuth):
    """Implementación de GitHubOAuth usando httpx para llamadas HTTP async."""

    # URLs de GitHub OAuth
    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_API_URL = "https://api.github.com/user"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ):
        """Inicializa el proveedor OAuth de GitHub.

        Args:
            client_id: Client ID de la aplicación GitHub OAuth
            client_secret: Client secret de la aplicación GitHub OAuth
            redirect_uri: URL de callback registrada en GitHub
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    def get_authorization_url(self, state: str) -> str:
        """Genera URL de autorización de GitHub.

        Args:
            state: Estado único para prevenir CSRF

        Returns:
            URL completa para redirigir al usuario al formulario de autorización de GitHub

        Raises:
            InfrastructureException: Error al generar URL (no debería ocurrir)
        """
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "state": state,
            "scope": "user:email"  # Permisos: leer email del usuario
        }

        query_string = urlencode(params)
        return f"{self.AUTHORIZE_URL}?{query_string}"

    async def exchange_code_for_token(self, code: str) -> str:
        """Intercambia authorization code por access token de GitHub.

        Args:
            code: Authorization code recibido en callback desde GitHub

        Returns:
            Access token de GitHub (string)

        Raises:
            InvalidTokenError: Code inválido, expirado o ya usado
            InfrastructureException: Error de red o respuesta inesperada
        """
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "redirect_uri": self._redirect_uri
        }

        headers = {
            "Accept": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.TOKEN_URL,
                    data=data,
                    headers=headers,
                    timeout=10.0
                )

                response_data = response.json()

                # GitHub devuelve error en el JSON si el code es inválido
                if "error" in response_data:
                    error_msg = response_data.get(
                        "error_description", response_data["error"])
                    raise InvalidTokenError(
                        f"GitHub OAuth token exchange failed: {error_msg}"
                    )

                # Extraer access token
                access_token = response_data.get("access_token")
                if not access_token:
                    raise InfrastructureException(
                        "GitHub OAuth response missing access_token"
                    )

                return access_token

        except httpx.HTTPError as e:
            raise InfrastructureException(
                f"GitHub OAuth token exchange failed: {str(e)}"
            ) from e
        except InvalidTokenError:
            # Re-raise sin wrap
            raise

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Obtiene información del usuario desde GitHub API.

        Args:
            access_token: Access token de GitHub obtenido previamente

        Returns:
            Dict con información del usuario:
                - id: GitHub user ID (int)
                - email: Email del usuario (str)
                - name: Nombre completo (str)
                - avatar_url: URL de avatar (str)
                - login: Username de GitHub (str)

        Raises:
            InvalidTokenError: Token inválido o expirado
            InfrastructureException: Error de red o respuesta inesperada
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.USER_API_URL,
                    headers=headers,
                    timeout=10.0
                )

                # GitHub devuelve 401 si el token es inválido
                if response.status_code == 401:
                    raise InvalidTokenError("Invalid GitHub access token")

                response.raise_for_status()

                user_data = response.json()

                # Retornar campos relevantes
                return {
                    "id": user_data.get("id"),
                    "email": user_data.get("email"),
                    "name": user_data.get("name"),
                    "avatar_url": user_data.get("avatar_url"),
                    "login": user_data.get("login")
                }

        except httpx.HTTPError as e:
            raise InfrastructureException(
                f"GitHub user info request failed: {str(e)}"
            ) from e
        except InvalidTokenError:
            # Re-raise sin wrap
            raise
