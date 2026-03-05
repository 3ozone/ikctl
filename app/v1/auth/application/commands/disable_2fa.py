"""Use Case: Deshabilitar autenticación de dos factores (2FA)."""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from app.v1.auth.application.interfaces.user_repository import UserRepository
from app.v1.auth.application.exceptions import ResourceNotFoundError
from app.v1.auth.domain.events.two_fa_disabled import TwoFADisabled
from app.v1.shared.application.interfaces.event_bus import EventBus


class Disable2FA:
    """Use Case para deshabilitar 2FA en una cuenta de usuario.

    Elimina el secret TOTP y marca 2FA como deshabilitado.
    """

    def __init__(self, user_repository: UserRepository, event_bus: Optional[EventBus] = None) -> None:
        self.user_repository = user_repository
        self._event_bus = event_bus

    async def execute(self, user_id: str) -> None:
        """Deshabilita 2FA para un usuario.

        Args:
            user_id: ID del usuario.

        Raises:
            ResourceNotFoundError: Si el usuario no existe.
        """
        # Buscar usuario
        user = await self.user_repository.find_by_id(user_id)
        if user is None:
            raise ResourceNotFoundError(
                f"Usuario con ID {user_id} no encontrado"
            )

        # Deshabilitar 2FA via entity command
        user.disable_2fa()
        user.updated_at = datetime.now(timezone.utc)

        # Persistir cambios
        await self.user_repository.update(user)

        if self._event_bus is not None:
            await self._event_bus.publish(
                TwoFADisabled(user_id=user_id, correlation_id=str(uuid4()))
            )
