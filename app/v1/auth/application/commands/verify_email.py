"""Use Case para verificar emails."""
from uuid import uuid4
from typing import Optional

from app.v1.auth.domain.entities import VerificationToken
from app.v1.auth.domain.events.email_verified import EmailVerified
from app.v1.shared.application.interfaces.event_bus import EventBus


class VerifyEmail:
    """Use Case para verificar que un email ha sido validado."""

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._event_bus = event_bus

    async def execute(
        self,
        verification_token: VerificationToken,
        user_email: str = ""
    ) -> bool:
        """Verifica si un token de email_verification es válido.

        Args:
            verification_token: VerificationToken entity con tipo "email_verification"
            user_email: Email del usuario (para el evento EmailVerified)

        Returns:
            True si el token es válido y no ha expirado

        Raises:
            InvalidVerificationTokenError: Si el token es inválido o ha expirado
        """
        result = verification_token.is_valid_for_email_verification()

        if self._event_bus is not None:
            await self._event_bus.publish(
                EmailVerified(
                    user_id=verification_token.user_id,
                    email=user_email,
                    correlation_id=str(uuid4())
                )
            )

        return result
