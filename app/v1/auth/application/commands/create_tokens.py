"""Use Case para crear tokens JWT y refresh token."""
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from jose import jwt

from app.v1.auth.domain.entities import User
from app.v1.auth.application.dtos.token_pair import TokenPair


class CreateTokens:
    """Use Case para crear access_token (JWT) y refresh_token.

    Acceso token: JWT con expiración de 30 minutos.
    Refresh token: Entity refrescable con expiración de 7 días.
    """

    # Configuración de tokens
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    ALGORITHM = "HS256"
    SECRET_KEY = "ikctl-secret-key-change-in-production"

    def execute(self, user: User) -> TokenPair:
        """Crea access_token y refresh_token para un usuario.

        Args:
            user: Usuario para el cual crear los tokens

        Returns:
            TokenPair con access_token, refresh_token y fechas de expiración
        """
        now = datetime.now(timezone.utc)

        # Crear access token (JWT)
        access_token_expires = now + \
            timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token_payload = {
            "sub": user.id,
            "email": user.email.value,
            "exp": access_token_expires,
            "iat": now
        }
        access_token = jwt.encode(
            access_token_payload,
            self.SECRET_KEY,
            algorithm=self.ALGORITHM
        )

        # Crear refresh token (token opaco aleatorio)
        refresh_token_expires = now + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token_value = str(uuid4())

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token_value,
            access_expires_at=access_token_expires,
            refresh_expires_at=refresh_token_expires,
        )
