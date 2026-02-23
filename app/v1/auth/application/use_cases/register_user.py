"""Use Case para registrar un nuevo usuario."""
from uuid import uuid4
from datetime import datetime, timezone

from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email


class RegisterUser:
    """Use Case para registrar un nuevo usuario en el sistema.

    Crea una nueva entidad User con validación de domain.
    """

    def execute(self, name: str, email: str, password_hash: str) -> User:
        """Registra un nuevo usuario.

        Args:
            name: Nombre del usuario
            email: Email del usuario (string, será convertido a Email VO)
            password_hash: Hash bcrypt de la contraseña

        Returns:
            Usuario creado (User entity)

        Raises:
            InvalidUserError: Si algún campo es inválido
            InvalidEmailError: Si el email es inválido
        """
        # Convertir string a Email Value Object (valida formato)
        email_vo = Email(email)

        # Generar timestamps
        now = datetime.now(timezone.utc)

        # Crear User entity (valida todos los campos en __post_init__)
        user = User(
            id=str(uuid4()),
            name=name,
            email=email_vo,
            password_hash=password_hash,
            created_at=now,
            updated_at=now
        )

        return user
