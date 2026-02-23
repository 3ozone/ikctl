"""Use Case: ChangePassword - Cambiar contraseña de usuario."""
from app.v1.auth.domain.entities import User
from app.v1.auth.domain.exceptions import InvalidUserError
from app.v1.auth.application.use_cases.hash_password import HashPassword
from app.v1.auth.application.use_cases.verify_password import VerifyPassword
from app.v1.auth.application.interfaces.password_history_repository import IPasswordHistoryRepository
from app.v1.auth.application.exceptions import UnauthorizedOperationError


class ChangePassword:
    """Use Case para cambiar contraseña de usuario."""

    def __init__(
        self,
        hash_password: HashPassword,
        verify_password: VerifyPassword,
        password_history_repository: IPasswordHistoryRepository
    ):
        """
        Inyectar dependencias.

        Args:
            hash_password: Use case para hashear contraseñas
            verify_password: Use case para verificar contraseñas
            password_history_repository: Repositorio de historial de contraseñas (RN-07)
        """
        self.hash_password = hash_password
        self.verify_password = verify_password
        self.password_history_repository = password_history_repository

    async def execute(self, user: User, current_password: str, new_password: str) -> User:
        """
        Cambiar contraseña de usuario.

        Args:
            user: Usuario actual
            current_password: Contraseña actual en texto plano
            new_password: Nueva contraseña en texto plano

        Returns:
            User: Usuario con password_hash actualizado

        Raises:
            InvalidUserError: Si current_password es incorrecto
            UnauthorizedOperationError: Si intenta reutilizar una de las últimas 3 contraseñas (RN-07)
        """
        # Verificar que la contraseña actual sea correcta
        if not self.verify_password.execute(current_password, user.password_hash):
            raise InvalidUserError("Current password is incorrect")

        # RN-07: Validar que la nueva contraseña no esté en las últimas 3
        password_history = await self.password_history_repository.find_last_n_by_user(
            user.id, 3
        )

        # Verificar si la nueva contraseña coincide con alguna del historial
        new_password_hash = self.hash_password.execute(new_password)
        for history_entry in password_history:
            if self.verify_password.execute(new_password, history_entry.password_hash):
                raise UnauthorizedOperationError(
                    "No puedes reutilizar una de tus últimas 3 contraseñas"
                )

        # Actualizar usuario con nueva contraseña
        user.password_hash = new_password_hash

        # Guardar nueva contraseña en historial (RN-07)
        await self.password_history_repository.save(user.id, new_password_hash)

        return user
