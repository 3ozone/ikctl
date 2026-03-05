"""Use Case para registrar un nuevo usuario."""
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional

from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email
from app.v1.auth.application.dtos.registration_result import RegistrationResult
from app.v1.auth.domain.events.user_registered import UserRegistered
from app.v1.shared.application.interfaces.event_bus import EventBus


class RegisterUser:
    """Use Case para registrar un nuevo usuario en el sistema."""

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._event_bus = event_bus

    async def execute(self, name: str, email: str, password_hash: str) -> RegistrationResult:
        """Registra un nuevo usuario.

        Args:
            name: Nombre del usuario
            email: Email del usuario (string, será convertido a Email VO)
            password_hash: Hash bcrypt de la contraseña

        Returns:
            RegistrationResult con user_id, email y flag de verificación enviada

        Raises:
            InvalidUserError: Si algún campo es inválido
            InvalidEmailError: Si el email es inválido
        """
        email_vo = Email(email)
        now = datetime.now(timezone.utc)

        user = User(
            id=str(uuid4()),
            name=name,
            email=email_vo,
            password_hash=password_hash,
            created_at=now,
            updated_at=now
        )

        if self._event_bus is not None:
            await self._event_bus.publish(
                UserRegistered(
                    user_id=user.id,
                    email=user.email.value,
                    correlation_id=str(uuid4())
                )
            )

        return RegistrationResult(
            user_id=user.id,
            email=user.email.value,
            verification_token_sent=False
        )
