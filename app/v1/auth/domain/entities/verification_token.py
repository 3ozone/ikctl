"""Entity VerificationToken."""
from dataclasses import dataclass
from datetime import datetime, timezone

from app.v1.auth.domain.exceptions import InvalidVerificationTokenError


@dataclass
class VerificationToken:
    """Entity VerificationToken para verificaciones (email, password reset).

    Una Entity con identidad (id) que puede mutar.
    Almacena tokens de verificación de email y reset de contraseña.
    """
    id: str
    user_id: str
    token: str
    token_type: str  # "email_verification" o "password_reset"
    expires_at: datetime
    created_at: datetime

    def __post_init__(self) -> None:
        """Valida que los datos de VerificationToken sean válidos."""
        if not self.id or not isinstance(self.id, str):
            raise InvalidVerificationTokenError(
                "El ID del token no puede estar vacío"
            )

        if not self.user_id or not isinstance(self.user_id, str):
            raise InvalidVerificationTokenError(
                "El user_id no puede estar vacío")

        if not self.token or not isinstance(self.token, str):
            raise InvalidVerificationTokenError(
                "El token no puede estar vacío")

        if self.token_type not in ("email_verification", "password_reset"):
            raise InvalidVerificationTokenError(
                f"token_type debe ser 'email_verification' o 'password_reset', "
                f"no '{self.token_type}'"
            )

        if not isinstance(self.expires_at, datetime):
            raise InvalidVerificationTokenError(
                "expires_at debe ser un datetime")

        if not isinstance(self.created_at, datetime):
            raise InvalidVerificationTokenError(
                "created_at debe ser un datetime")

    def __eq__(self, other: object) -> bool:
        """Igualdad por identidad: dos VerificationToken son iguales si tienen el mismo id."""
        return isinstance(other, VerificationToken) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def is_valid_for_email_verification(self) -> bool:
        """Valida si el token es válido para verificación de email.

        Returns:
            True si el token es válido

        Raises:
            InvalidVerificationTokenError: Si el token es inválido o ha expirado
        """
        if self.token_type != "email_verification":
            raise InvalidVerificationTokenError(
                "El token no es de verificación de email"
            )

        now = datetime.now(timezone.utc)
        if self.expires_at <= now:
            raise InvalidVerificationTokenError(
                "El token de verificación de email ha expirado"
            )

        return True

    def is_valid_for_password_reset(self) -> bool:
        """Valida si el token es válido para reset de contraseña.

        Returns:
            True si el token es válido

        Raises:
            InvalidVerificationTokenError: Si el token es inválido o ha expirado
        """
        if self.token_type != "password_reset":
            raise InvalidVerificationTokenError(
                "El token no es de reset de contraseña"
            )

        now = datetime.now(timezone.utc)
        if self.expires_at <= now:
            raise InvalidVerificationTokenError(
                "El token de reset de contraseña ha expirado"
            )

        return True
