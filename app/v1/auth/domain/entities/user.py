"""Entity User."""
from dataclasses import dataclass
from datetime import datetime

from app.v1.auth.domain.value_objects import Email
from app.v1.auth.domain.exceptions import InvalidUserError


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
    totp_secret: str | None = None
    is_2fa_enabled: bool = False
    is_email_verified: bool = False

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

        if self.totp_secret is not None and not isinstance(self.totp_secret, str):
            raise InvalidUserError("totp_secret debe ser un string o None")

        if not isinstance(self.is_2fa_enabled, bool):
            raise InvalidUserError("is_2fa_enabled debe ser un booleano")

        if not isinstance(self.is_email_verified, bool):
            raise InvalidUserError("is_email_verified debe ser un booleano")

    def __eq__(self, other: object) -> bool:
        """Igualdad por identidad: dos User son iguales si tienen el mismo id."""
        return isinstance(other, User) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    # --- Comandos ---

    def enable_2fa(self, secret: str) -> None:
        """Activa el segundo factor de autenticación con el secreto TOTP dado.

        Args:
            secret: Secreto TOTP en formato Base32.
        """
        self.totp_secret = secret
        self.is_2fa_enabled = True

    def disable_2fa(self) -> None:
        """Desactiva el segundo factor de autenticación y borra el secreto TOTP."""
        self.totp_secret = None
        self.is_2fa_enabled = False

    def verify_email(self) -> None:
        """Marca el email del usuario como verificado."""
        self.is_email_verified = True

    def update_name(self, name: str) -> None:
        """Actualiza el nombre del usuario.

        Args:
            name: Nuevo nombre del usuario.

        Raises:
            InvalidUserError: Si el nombre está vacío.
        """
        if not name or not isinstance(name, str):
            raise InvalidUserError(
                "El nombre del usuario no puede estar vacío")
        self.name = name

    def update_password(self, password_hash: str) -> None:
        """Actualiza el hash de contraseña del usuario.

        Args:
            password_hash: Nuevo hash de la contraseña.

        Raises:
            InvalidUserError: Si el hash está vacío.
        """
        if not password_hash or not isinstance(password_hash, str):
            raise InvalidUserError("El hash de password no puede estar vacío")
        self.password_hash = password_hash

    # --- Queries ---

    def is_verified(self) -> bool:
        """Indica si el email del usuario ha sido verificado.

        Returns:
            True si el email está verificado, False en caso contrario.
        """
        return self.is_email_verified

    def is_2fa_required(self) -> bool:
        """Indica si el usuario tiene 2FA activado.

        Returns:
            True si is_2fa_enabled es True, False en caso contrario.
        """
        return self.is_2fa_enabled

    def has_oauth_password(self) -> bool:
        """Indica si el usuario se registró vía OAuth (sin contraseña propia).

        Returns:
            True si password_hash es el sentinel OAUTH_NO_PASSWORD.
        """
        return self.password_hash == "OAUTH_NO_PASSWORD"
