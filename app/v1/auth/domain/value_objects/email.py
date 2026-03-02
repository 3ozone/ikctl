"""Value Object Email."""
import re
from dataclasses import dataclass

from app.v1.auth.domain.exceptions import InvalidEmailError

# Regex simple para validar email RFC 5322 (versión simplificada)
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"


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
