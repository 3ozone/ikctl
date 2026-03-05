"""Use Case para solicitar reset de contraseña."""
from app.v1.auth.domain.entities import User
from app.v1.auth.application.commands.generate_verification_token import GenerateVerificationToken
from app.v1.auth.application.dtos.verification_result import VerificationResult


class RequestPasswordReset:
    """Use Case para solicitar el reset de una contraseña.

    Genera un token de password_reset para que el usuario pueda cambiar su contraseña de forma segura.
    """

    def __init__(self, generate_verification_token: GenerateVerificationToken):
        """Inicializa con una instancia de GenerateVerificationToken.

        Args:
            generate_verification_token: Instancia para generar tokens de verificación
        """
        self.generate_verification_token = generate_verification_token

    def execute(self, user: User) -> VerificationResult:
        """Genera un token de password_reset para un usuario.

        Args:
            user: Usuario que solicita reset de contraseña

        Returns:
            VerificationResult con success=True y user_id
        """
        # Generar token de password_reset
        self.generate_verification_token.execute(
            user_id=user.id,
            token_type="password_reset"
        )

        return VerificationResult(success=True, user_id=user.id)
