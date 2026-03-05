"""Use Case: ChangePassword - Cambiar contraseña de usuario."""
from uuid import uuid4
from typing import Optional

from app.v1.auth.domain.entities import User
from app.v1.auth.domain.exceptions import InvalidUserError
from app.v1.auth.application.queries.hash_password import HashPassword
from app.v1.auth.application.queries.verify_password import VerifyPassword
from app.v1.auth.application.interfaces.password_history_repository import PasswordHistoryRepository
from app.v1.auth.application.exceptions import UnauthorizedOperationError
from app.v1.auth.application.dtos.password_change_result import PasswordChangeResult
from app.v1.auth.domain.events.password_changed import PasswordChanged
from app.v1.shared.application.interfaces.event_bus import EventBus


class ChangePassword:
    """Use Case para cambiar contraseña de usuario."""

    def __init__(
        self,
        hash_password: HashPassword,
        verify_password: VerifyPassword,
        password_history_repository: PasswordHistoryRepository,
        event_bus: Optional[EventBus] = None
    ):
        self.hash_password = hash_password
        self.verify_password = verify_password
        self.password_history_repository = password_history_repository
        self._event_bus = event_bus

    async def execute(self, user: User, current_password: str, new_password: str) -> PasswordChangeResult:
        """
        Cambiar contraseña de usuario.

        Args:
            user: Usuario actual
            current_password: Contraseña actual en texto plano
            new_password: Nueva contraseña en texto plano

        Returns:
            PasswordChangeResult: Resultado del cambio de contraseña

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

        # Actualizar usuario con nueva contraseña via entity command
        user.update_password(new_password_hash)

        # Guardar nueva contraseña en historial (RN-07)
        await self.password_history_repository.save(user.id, new_password_hash)

        if self._event_bus is not None:
            await self._event_bus.publish(
                PasswordChanged(user_id=user.id, correlation_id=str(uuid4()))
            )

        return PasswordChangeResult(success=True, user_id=user.id)
