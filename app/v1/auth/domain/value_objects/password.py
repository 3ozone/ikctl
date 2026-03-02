"""Value Object Password."""
import re
from dataclasses import dataclass

from app.v1.auth.domain.exceptions import InvalidPasswordError

# Patrones para validar password
MIN_PASSWORD_LENGTH = 8
HAS_UPPERCASE = r"[A-Z]"
HAS_LOWERCASE = r"[a-z]"
HAS_DIGIT = r"\d"


@dataclass(frozen=True)
class Password:
    """Value Object para representar una contraseña.

    Immutable (frozen=True) para garantizar que no cambie una vez creado.
    Valida complejidad de contraseña en la construcción:
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
