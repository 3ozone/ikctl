"""Use Case para refrescar access tokens."""
from datetime import datetime, timezone, timedelta
from jose import jwt

from app.v1.auth.domain.entities import RefreshToken
from app.v1.auth.domain.exceptions import InvalidRefreshTokenError


class RefreshAccessToken:
    """Use Case para generar un nuevo access token usando un refresh token.

    Verifica que el refresh token sea válido y no haya expirado,
    luego genera un nuevo access token para el usuario asociado.
    """

    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    ALGORITHM = "HS256"
    SECRET_KEY = "ikctl-secret-key-change-in-production"

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
        if refresh_token.expires_at <= now:
            raise InvalidRefreshTokenError("Refresh token ha expirado")

        # Crear nuevo access token para el user_id del refresh token
        access_token_expires = now + \
            timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token_payload = {
            "sub": refresh_token.user_id,
            "exp": access_token_expires,
            "iat": now
        }

        new_access_token = jwt.encode(
            access_token_payload,
            self.SECRET_KEY,
            algorithm=self.ALGORITHM
        )

        return new_access_token
