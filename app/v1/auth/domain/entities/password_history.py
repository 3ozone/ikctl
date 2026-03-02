"""Entity PasswordHistory."""
from dataclasses import dataclass
from datetime import datetime

from app.v1.auth.domain.exceptions import InvalidPasswordHistoryError


@dataclass
class PasswordHistory:
    """Entity PasswordHistory para almacenar historial de contraseñas.

    Una Entity con identidad (id) que puede mutar.
    Almacena las contraseñas hasheadas del usuario para validar RN-07:
    no permitir reutilización de las últimas 3 contraseñas.
    """
    id: str
    user_id: str
    password_hash: str
    created_at: datetime

    def __post_init__(self) -> None:
        """Valida que los datos de PasswordHistory sean válidos."""
        if not self.id or not isinstance(self.id, str):
            raise InvalidPasswordHistoryError(
                "El ID del historial no puede estar vacío"
            )

        if not self.user_id or not isinstance(self.user_id, str):
            raise InvalidPasswordHistoryError(
                "El user_id no puede estar vacío")

        if not self.password_hash or not isinstance(self.password_hash, str):
            raise InvalidPasswordHistoryError(
                "El password_hash no puede estar vacío"
            )

        if not isinstance(self.created_at, datetime):
            raise InvalidPasswordHistoryError(
                "created_at debe ser un datetime")

    def __eq__(self, other: object) -> bool:
        """Igualdad por identidad: dos PasswordHistory son iguales si tienen el mismo id."""
        return isinstance(other, PasswordHistory) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
