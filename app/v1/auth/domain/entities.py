"""Entidades del módulo de autenticación."""
from dataclasses import dataclass
from datetime import datetime, timezone

from app.v1.auth.domain.value_objects import Email
from app.v1.auth.domain.exceptions import (
    InvalidUserError,
    InvalidRefreshTokenError,
    InvalidVerificationTokenError,
)


@dataclass
class User:
    """Entity User que representa un usuario en el sistema.

    Una Entity tiene identidad (id) y puede mutar su estado.
    Contiene Value Objects como email.
    """
    id: str
    name: str
    email: Email
    password_hash: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """Valida que los datos de User sean válidos."""
        if not self.id or not isinstance(self.id, str):
            raise InvalidUserError("El ID del usuario no puede estar vacío")

        if not self.name or not isinstance(self.name, str):
            raise InvalidUserError(
                "El nombre del usuario no puede estar vacío")

        if not self.password_hash or not isinstance(self.password_hash, str):
            raise InvalidUserError("El hash de password no puede estar vacío")

        if not isinstance(self.email, Email):
            raise InvalidUserError("El usuario debe tener un Email válido")

        if not isinstance(self.created_at, datetime):
            raise InvalidUserError("created_at debe ser un datetime")

        if not isinstance(self.updated_at, datetime):
            raise InvalidUserError("updated_at debe ser un datetime")


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

    def is_valid_for_email_verification(self) -> bool:
        """Valida si el token es válido para verificación de email.

        Verifica que:
        - token_type sea "email_verification"
        - El token no haya expirado

        Returns:
            True si el token es válido

        Raises:
            InvalidVerificationTokenError: Si el token es inválido o ha expirado
        """
        # Verificar que el token_type sea email_verification
        if self.token_type != "email_verification":
            raise InvalidVerificationTokenError(
                "El token no es de verificación de email"
            )

        # Verificar que el token no haya expirado
        now = datetime.now(timezone.utc)
        if self.expires_at <= now:
            raise InvalidVerificationTokenError(
                "El token de verificación de email ha expirado"
            )

        return True

    def is_valid_for_password_reset(self) -> bool:
        """Valida si el token es válido para reset de contraseña.

        Verifica que:
        - token_type sea "password_reset"
        - El token no haya expirado

        Returns:
            True si el token es válido

        Raises:
            InvalidVerificationTokenError: Si el token es inválido o ha expirado
        """
        # Verificar que el token_type sea password_reset
        if self.token_type != "password_reset":
            raise InvalidVerificationTokenError(
                "El token no es de reset de contraseña"
            )

        # Verificar que el token no haya expirado
        now = datetime.now(timezone.utc)
        if self.expires_at <= now:
            raise InvalidVerificationTokenError(
                "El token de reset de contraseña ha expirado"
            )

        return True
