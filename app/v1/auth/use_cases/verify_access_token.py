"""Use Case para verificar access tokens JWT."""
from jose import jwt, JWTError

from app.v1.auth.domain.exceptions import InvalidJWTTokenError


class VerifyAccessToken:
    """Use Case para verificar y decodificar access tokens JWT.

    Valida la firma del token, verifica la expiración y retorna el payload.
    """

    ALGORITHM = "HS256"
    SECRET_KEY = "ikctl-secret-key-change-in-production"

    def execute(self, access_token: str) -> dict:
        """Verifica y decodifica un access token JWT.

        Args:
            access_token: Token JWT a verificar

        Returns:
            Payload decodificado del token

        Raises:
            InvalidJWTTokenError: Si el token es inválido, expirado o la firma no es válida
        """
        try:
            # Decodificar y verificar el JWT
            payload = jwt.decode(
                access_token,
                self.SECRET_KEY,
                algorithms=[self.ALGORITHM]
            )
            return payload
        except JWTError as e:
            # Capturar cualquier error de JWT (expiración, firma inválida, etc)
            raise InvalidJWTTokenError(
                f"Token inválido o expirado: {str(e)}") from e
