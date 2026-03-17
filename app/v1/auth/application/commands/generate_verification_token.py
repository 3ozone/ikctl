"""Use Case para generar tokens de verificación."""
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.v1.auth.domain.entities import VerificationToken
from app.v1.auth.application.dtos.verification_result import VerificationResult
from app.v1.auth.application.interfaces.verification_token_repository import VerificationTokenRepository


class GenerateVerificationToken:
    """Use Case para generar tokens de verificación de email y reset de contraseña.

    Crea VerificationToken entities únicas con expiración.
    """

    # Tiempos de expiración por tipo de token
    EXPIRATION_HOURS = {
        "email_verification": 24,
        "password_reset": 1
    }

    def __init__(
        self,
        verification_token_repository: Optional[VerificationTokenRepository] = None,
    ) -> None:
        self._repository = verification_token_repository

    async def execute(self, user_id: str, token_type: str) -> VerificationResult:
        """Genera un token de verificación para un usuario.

        Args:
            user_id: ID del usuario para el cual generar el token
            token_type: Tipo de token ("email_verification" o "password_reset")

        Returns:
            VerificationResult con success=True, user_id y el valor del token generado

        Raises:
            InvalidVerificationTokenError: Si token_type es inválido (validación en Entity)
        """
        now = datetime.now(timezone.utc)

        # Obtener horas de expiración según tipo
        hours = self.EXPIRATION_HOURS.get(token_type, 24)
        expires_at = now + timedelta(hours=hours)

        token_value = str(uuid4())

        verification_token = VerificationToken(
            id=str(uuid4()),
            user_id=user_id,
            token=token_value,
            token_type=token_type,
            expires_at=expires_at,
            created_at=now
        )

        if self._repository is not None:
            await self._repository.save(verification_token)

        return VerificationResult(success=True, user_id=user_id, token=token_value)
