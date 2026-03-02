"""Value Object JWTToken."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any

from app.v1.auth.domain.exceptions import InvalidJWTTokenError


@dataclass(frozen=True)
class JWTToken:
    """Value Object para representar un JWT Token.

    Immutable (frozen=True) para garantizar integridad del token.
    Contiene el token string, su payload decodificado y el tipo (access/refresh).
    """
    token: str
    payload: Dict[str, Any]
    token_type: str  # "access" o "refresh"

    def __post_init__(self) -> None:
        """Valida que el JWT Token sea válido."""
        if not self.token or not isinstance(self.token, str):
            raise InvalidJWTTokenError("El token no puede estar vacío")

        if not self.payload or not isinstance(self.payload, dict):
            raise InvalidJWTTokenError(
                "El payload debe ser un diccionario válido")

        if self.token_type not in ("access", "refresh"):
            raise InvalidJWTTokenError(
                f"token_type debe ser 'access' o 'refresh', no '{self.token_type}'"
            )

    def get_user_id(self) -> str:
        """Extrae el user_id del payload del token.

        Returns:
            El identificador del usuario contenido en el payload.
        """
        return self.payload["user_id"]

    def get_expiration(self) -> datetime:
        """Extrae la fecha de expiración del payload como datetime UTC.

        Returns:
            La fecha de expiración del token como datetime con tzinfo UTC.
        """
        return datetime.fromtimestamp(self.payload["exp"], tz=timezone.utc)

    def is_expired(self) -> bool:
        """Comprueba si el token ha expirado comparando exp con la hora actual UTC.

        Returns:
            True si el token ha expirado, False si aún es válido.
        """
        return datetime.now(tz=timezone.utc) > self.get_expiration()

    def is_access_token(self) -> bool:
        """Indica si este token es de tipo access.

        Returns:
            True si token_type == 'access', False en caso contrario.
        """
        return self.token_type == "access"

    def is_refresh_token(self) -> bool:
        """Indica si este token es de tipo refresh.

        Returns:
            True si token_type == 'refresh', False en caso contrario.
        """
        return self.token_type == "refresh"
