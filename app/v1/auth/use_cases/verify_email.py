"""Use Case para verificar emails."""
from app.v1.auth.domain.entities import VerificationToken


class VerifyEmail:
    """Use Case para verificar que un email ha sido validado.

    Orquesta la validación del token usando el método de dominio.
    """

    def execute(self, verification_token: VerificationToken) -> bool:
        """Verifica si un token de email_verification es válido.

        Args:
            verification_token: VerificationToken entity con tipo "email_verification"

        Returns:
            True si el token es válido y no ha expirado

        Raises:
            InvalidVerificationTokenError: Si el token es inválido o ha expirado
        """
        # Usar el método de validación de dominio
        return verification_token.is_valid_for_email_verification()
