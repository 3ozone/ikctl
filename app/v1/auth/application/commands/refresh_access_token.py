"""Use Case para refrescar access tokens."""
from datetime import datetime, timezone

from app.v1.auth.application.interfaces.jwt_provider import JWTProvider
from app.v1.auth.domain.entities import RefreshToken
from app.v1.auth.domain.exceptions import InvalidRefreshTokenError


class RefreshAccessToken:
    """Use Case para generar un nuevo access token usando un refresh token.

    Verifica que el refresh token sea válido y no haya expirado,
    luego genera un nuevo access token para el usuario asociado.
    """

    ACCESS_TOKEN_EXPIRE_MINUTES = 30

    def __init__(self, jwt_provider: JWTProvider) -> None:
        """Inicializa el use case con el proveedor JWT.

        Args:
            jwt_provider: Proveedor JWT para generar tokens con la clave correcta.
        """
        self._jwt_provider = jwt_provider

    def execute(self, refresh_token: RefreshToken) -> str:
        """Genera un nuevo access token usando un refresh token válido.

        Args:
            refresh_token: RefreshToken entity con el user_id almacenado

        Returns:
            Nuevo access token (JWT) como string

        Raises:
            InvalidRefreshTokenError: Si el refresh token ha expirado
        """
        now = datetime.now(timezone.utc)

        # Verificar que el refresh token no ha expirado
        expires_at = refresh_token.expires_at if refresh_token.expires_at.tzinfo else refresh_token.expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            raise InvalidRefreshTokenError("Refresh token ha expirado")

        token = self._jwt_provider.create_access_token(refresh_token.user_id)
        return token.token
