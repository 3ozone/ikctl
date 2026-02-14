"""Use Case para autenticar un usuario."""
from app.v1.auth.domain.entities import User
from app.v1.auth.domain.exceptions import InvalidUserError
from app.v1.auth.use_cases.verify_password import VerifyPassword


class AuthenticateUser:
    """Use Case para autenticar un usuario verificando su contraseña.

    Utiliza VerifyPassword inyectado para verificar la contraseña.
    Patrón de inyección de dependencia para reutilizar lógica.
    """

    def __init__(self, verify_password: VerifyPassword):
        """Inicializa con una instancia de VerifyPassword.

        Args:
            verify_password: Instancia de VerifyPassword para verificar contraseñas
        """
        self.verify_password = verify_password

    def execute(self, plaintext_password: str, user: User) -> User:
        """Autentica un usuario verificando su contraseña.

        Args:
            plaintext_password: Contraseña en texto plano a verificar
            user: Usuario con el hash de contraseña almacenado

        Returns:
            El usuario si la autenticación es exitosa

        Raises:
            InvalidUserError: Si la contraseña es incorrecta
        """
        # Verificar que la contraseña coincida con el hash
        is_valid = self.verify_password.execute(
            plaintext_password, user.password_hash)

        if not is_valid:
            raise InvalidUserError("Contraseña incorrecta")

        return user
