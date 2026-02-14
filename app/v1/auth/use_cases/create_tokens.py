"""Use Case para crear tokens JWT y refresh token."""
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from jose import jwt

from app.v1.auth.domain.entities import User, RefreshToken


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

    def execute(self, user: User) -> dict:
        """Crea access_token y refresh_token para un usuario.

        Args:
            user: Usuario para el cual crear los tokens

        Returns:
            Diccionario con:
                - access_token: JWT firmado (string)
                - refresh_token: RefreshToken entity
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

        # Crear refresh token (Entity)
        refresh_token_expires = now + \
            timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = RefreshToken(
            id=str(uuid4()),
            user_id=user.id,
            token=str(uuid4()),  # Token único aleatorio
            expires_at=refresh_token_expires,
            created_at=now
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
