"""Entity RefreshToken."""
from dataclasses import dataclass
from datetime import datetime

from app.v1.auth.domain.exceptions import InvalidRefreshTokenError


@dataclass
class RefreshToken:
    """Entity RefreshToken para almacenar tokens de refresco.

    Una Entity con identidad (id) que puede mutar.
    Almacena el token JWT y cuándo expira.
    """
    id: str
    user_id: str
    token: str
    expires_at: datetime
    created_at: datetime

    def __post_init__(self) -> None:
        """Valida que los datos de RefreshToken sean válidos."""
        if not self.id or not isinstance(self.id, str):
            raise InvalidRefreshTokenError(
                "El ID del token no puede estar vacío")

        if not self.user_id or not isinstance(self.user_id, str):
            raise InvalidRefreshTokenError("El user_id no puede estar vacío")

        if not self.token or not isinstance(self.token, str):
            raise InvalidRefreshTokenError("El token no puede estar vacío")

        if not isinstance(self.expires_at, datetime):
            raise InvalidRefreshTokenError("expires_at debe ser un datetime")

        if not isinstance(self.created_at, datetime):
            raise InvalidRefreshTokenError("created_at debe ser un datetime")

    def __eq__(self, other: object) -> bool:
        """Igualdad por identidad: dos RefreshToken son iguales si tienen el mismo id."""
        return isinstance(other, RefreshToken) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def is_expired(self) -> bool:
        """Comprueba si el token de refresco ha expirado.

        Returns:
            True si expires_at está en el pasado, False si aún es válido.
        """
        return datetime.now() > self.expires_at
