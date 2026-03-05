"""Use Case: Habilitar autenticación de dos factores (2FA)."""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from app.v1.auth.application.interfaces.user_repository import UserRepository
from app.v1.auth.application.interfaces.totp_provider import TOTPProvider
from app.v1.auth.application.exceptions import ResourceNotFoundError
from app.v1.auth.application.dtos.totp_setup import TOTPSetup
from app.v1.auth.domain.events.two_fa_enabled import TwoFAEnabled
from app.v1.shared.application.interfaces.event_bus import EventBus


class Enable2FA:
    """Use Case para habilitar 2FA en una cuenta de usuario.

    Genera un secret TOTP y un QR code para escanear con apps 2FA.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        totp_provider: TOTPProvider,
        event_bus: Optional[EventBus] = None
    ) -> None:
        self.user_repository = user_repository
        self.totp_provider = totp_provider
        self._event_bus = event_bus

    async def execute(self, user_id: str) -> TOTPSetup:
        """Habilita 2FA para un usuario.

        Args:
            user_id: ID del usuario.

        Returns:
            TOTPSetup con secret y qr_code_uri.

        Raises:
            ResourceNotFoundError: Si el usuario no existe.
        """
        # Buscar usuario
        user = await self.user_repository.find_by_id(user_id)
        if user is None:
            raise ResourceNotFoundError(
                f"Usuario con ID {user_id} no encontrado"
            )

        # Generar secret TOTP
        secret = self.totp_provider.generate_secret()

        # Generar QR code
        qr_code = self.totp_provider.generate_qr_code(
            secret=secret,
            user_email=user.email.value,
            issuer="ikctl"
        )

        # Actualizar usuario con 2FA habilitado via entity command
        user.enable_2fa(secret)
        user.updated_at = datetime.now(timezone.utc)

        # Persistir cambios
        await self.user_repository.update(user)

        if self._event_bus is not None:
            await self._event_bus.publish(
                TwoFAEnabled(user_id=user_id, correlation_id=str(uuid4()))
            )

        # Retornar DTO con datos para configurar app 2FA
        return TOTPSetup(
            secret=secret,
            qr_code_uri=qr_code,
            provisioning_uri="",
            backup_codes=[]
        )
