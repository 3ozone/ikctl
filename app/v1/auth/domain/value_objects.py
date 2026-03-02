"""Value Objects del módulo de autenticación."""
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any

from app.v1.auth.domain.exceptions import (
    InvalidEmailError,
    InvalidPasswordError,
    InvalidJWTTokenError,
)


# Regex simple para validar email RFC 5322 (versión simplificada)
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

# Patrones para validar password
MIN_PASSWORD_LENGTH = 8
HAS_UPPERCASE = r"[A-Z]"
HAS_LOWERCASE = r"[a-z]"
HAS_DIGIT = r"\d"


@dataclass(frozen=True)
class Email:
    """Value Object para representar un email.

    Immutable (frozen=True) para garantizar que no cambie una vez creado.
    Valida el formato del email en la construcción.
    """
    value: str

    def __post_init__(self) -> None:
        """Valida que el email tenga formato correcto."""
        if not self.value or not isinstance(self.value, str):
            raise InvalidEmailError("El email no puede estar vacío")

        if not re.match(EMAIL_REGEX, self.value):
            raise InvalidEmailError(
                f"El email '{self.value}' tiene un formato inválido")

    def normalized(self) -> str:
        """Devuelve el email en minúsculas para comparaciones.

        Returns:
            Email en minúsculas.
        """
        return self.value.lower()

    def domain(self) -> str:
        """Devuelve la parte del dominio del email (tras el @).

        Returns:
            Dominio del email (ej: 'example.com').
        """
        return self.value.split("@")[1]


@dataclass(frozen=True)
class Password:
    """Value Object para representar una contraseña.

    Immutable (frozen=True) para garantizar que no cambie una vez creado.
    Valida comlejidad de contraseña en la construcción:
    - Mínimo 8 caracteres
    - Al menos una mayúscula
    - Al menos una minúscula
    - Al menos un dígito
    """
    value: str

    def __post_init__(self) -> None:
        """Valida que la contraseña cumpla requisitos de complejidad."""
        if not self.value or not isinstance(self.value, str):
            raise InvalidPasswordError("La contraseña no puede estar vacía")

        if len(self.value) < MIN_PASSWORD_LENGTH:
            raise InvalidPasswordError(
                f"La contraseña debe tener mínimo {MIN_PASSWORD_LENGTH} caracteres"
            )

        if not re.search(HAS_UPPERCASE, self.value):
            raise InvalidPasswordError(
                "La contraseña debe contener al menos una mayúscula"
            )

        if not re.search(HAS_LOWERCASE, self.value):
            raise InvalidPasswordError(
                "La contraseña debe contener al menos una minúscula"
            )

        if not re.search(HAS_DIGIT, self.value):
            raise InvalidPasswordError(
                "La contraseña debe contener al menos un dígito"
            )


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
