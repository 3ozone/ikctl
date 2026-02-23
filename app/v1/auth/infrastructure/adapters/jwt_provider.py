"""JWTProvider - Implementación concreta de IJWTProvider usando python-jose."""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from jose import jwt, JWTError, ExpiredSignatureError

from app.v1.auth.application.interfaces.jwt_provider import IJWTProvider
from app.v1.auth.domain.value_objects import JWTToken
from app.v1.auth.application.exceptions import InvalidTokenError, TokenExpiredError
from app.v1.auth.infrastructure.exceptions import InfrastructureException


class JWTProvider(IJWTProvider):
    """Implementación de IJWTProvider usando python-jose."""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7
    ):
        """Inicializa el proveedor JWT.

        Args:
            secret_key: Clave secreta para firmar tokens
            algorithm: Algoritmo de firma (HS256, RS256, etc.)
            access_token_expire_minutes: Minutos hasta expiración del access token
            refresh_token_expire_days: Días hasta expiración del refresh token
        """
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_token_expire_minutes = access_token_expire_minutes
        self._refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        user_id: str,
        additional_claims: Dict[str, Any] | None = None
    ) -> JWTToken:
        """Genera un JWT access token.

        Args:
            user_id: ID del usuario
            additional_claims: Claims adicionales opcionales

        Returns:
            JWTToken con access token (exp: 30 min)

        Raises:
            InfrastructureException: Error al generar token
        """
        try:
            now = datetime.now(timezone.utc)
            expires_at = now + \
                timedelta(minutes=self._access_token_expire_minutes)

            payload = {
                "sub": user_id,
                "exp": expires_at,
                "iat": now,
                "type": "access"
            }

            # Añadir claims adicionales si existen
            if additional_claims:
                payload.update(additional_claims)

            token_string = jwt.encode(
                payload,
                self._secret_key,
                algorithm=self._algorithm
            )

            return JWTToken(
                token=token_string,
                token_type="access",
                payload=payload
            )

        except Exception as e:
            raise InfrastructureException(
                f"Error creando access token: {str(e)}"
            ) from e

    def create_refresh_token(self, user_id: str) -> JWTToken:
        """Genera un JWT refresh token.

        Args:
            user_id: ID del usuario

        Returns:
            JWTToken con refresh token (exp: 7 días)

        Raises:
            InfrastructureException: Error al generar token
        """
        try:
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(days=self._refresh_token_expire_days)

            payload = {
                "sub": user_id,
                "exp": expires_at,
                "iat": now,
                "type": "refresh"
            }

            token_string = jwt.encode(
                payload,
                self._secret_key,
                algorithm=self._algorithm
            )

            return JWTToken(
                token=token_string,
                token_type="refresh",
                payload=payload
            )

        except Exception as e:
            raise InfrastructureException(
                f"Error creando refresh token: {str(e)}"
            ) from e

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decodifica y valida un JWT token.

        Args:
            token: Token JWT string

        Returns:
            Payload del token (claims)

        Raises:
            InvalidTokenError: Token inválido o malformado
            TokenExpiredError: Token expirado
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm]
            )
            return payload

        except ExpiredSignatureError as e:
            raise TokenExpiredError("El token ha expirado") from e

        except JWTError as e:
            raise InvalidTokenError(f"Token inválido: {str(e)}") from e

    def verify_token(self, token: str) -> bool:
        """Verifica si un token es válido y no ha expirado.

        Args:
            token: Token JWT string

        Returns:
            True si válido, False si no

        Raises:
            InfrastructureException: Error al verificar
        """
        try:
            self.decode_token(token)
            return True

        except (InvalidTokenError, TokenExpiredError):
            return False

        except Exception as e:
            raise InfrastructureException(
                f"Error verificando token: {str(e)}"
            ) from e
