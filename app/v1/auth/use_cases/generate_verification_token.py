"""Use Case para generar tokens de verificación."""
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from app.v1.auth.domain.entities import VerificationToken


class GenerateVerificationToken:
    """Use Case para generar tokens de verificación de email y reset de contraseña.

    Crea VerificationToken entities únicas con expiración.
    """

    # Tiempos de expiración por tipo de token
    EXPIRATION_HOURS = {
        "email_verification": 24,
        "password_reset": 24
    }

    def execute(self, user_id: str, token_type: str) -> VerificationToken:
        """Genera un token de verificación para un usuario.

        Args:
            user_id: ID del usuario para el cual generar el token
            token_type: Tipo de token ("email_verification" o "password_reset")

        Returns:
            VerificationToken entity

        Raises:
            InvalidVerificationTokenError: Si token_type es inválido (validación en Entity)
        """
        now = datetime.now(timezone.utc)

        # Obtener horas de expiración según tipo
        hours = self.EXPIRATION_HOURS.get(token_type, 24)
        expires_at = now + timedelta(hours=hours)

        # Crear token de verificación
        verification_token = VerificationToken(
            id=str(uuid4()),
            user_id=user_id,
            token=str(uuid4()),  # Token único aleatorio
            token_type=token_type,
            expires_at=expires_at,
            created_at=now
        )

        return verification_token
