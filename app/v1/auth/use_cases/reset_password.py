"""Use Case para resetear contraseña."""
from datetime import datetime, timezone

from app.v1.auth.domain.entities import User, VerificationToken
from app.v1.auth.use_cases.hash_password import HashPassword
from app.v1.auth.domain.exceptions import InvalidVerificationTokenError


class ResetPassword:
    """Use Case para resetear la contraseña de un usuario.

    Valida el token de password_reset y actualiza la contraseña del usuario.
    """

    def __init__(self, hash_password: HashPassword):
        """Inicializa con una instancia de HashPassword.

        Args:
            hash_password: Instancia para hashear la nueva contraseña
        """
        self.hash_password = hash_password

    def execute(self, user: User, reset_token: VerificationToken, new_password: str) -> User:
        """Resetea la contraseña de un usuario.

        Args:
            user: Usuario cuya contraseña será reseteada
            reset_token: VerificationToken con tipo "password_reset"
            new_password: Nueva contraseña en texto plano

        Returns:
            Usuario actualizado con la nueva contraseña hasheada

        Raises:
            InvalidVerificationTokenError: Si el token es inválido o ha expirado
            InvalidPasswordError: Si la nueva contraseña es inválida
        """
        # Validar que el token de password_reset sea válido
        # El método de dominio lanzará excepción si no es válido
        reset_token.is_valid_for_password_reset()

        # Hashear la nueva contraseña (Password VO valida en su __post_init__)
        new_password_hash = self.hash_password.execute(new_password)

        # Actualizar el usuario con la nueva contraseña hasheada
        user.password_hash = new_password_hash
        user.updated_at = datetime.now(timezone.utc)

        return user
