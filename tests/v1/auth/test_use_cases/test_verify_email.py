"""Tests para Use Case VerifyEmail."""
from datetime import datetime, timezone, timedelta
import pytest

from app.v1.auth.domain.entities import VerificationToken
from app.v1.auth.domain.exceptions import InvalidVerificationTokenError
from app.v1.auth.use_cases.verify_email import VerifyEmail


class TestVerifyEmail:
    """Tests del Use Case VerifyEmail."""

    def test_verify_email_success(self):
        """Test 1: VerifyEmail verifica un token de email válido y retorna True."""
        verify_email_uc = VerifyEmail()

        now = datetime.now(timezone.utc)

        # Creamos un token de verificación de email válido
        verification_token = VerificationToken(
            id="token-123",
            user_id="user-123",
            token="email-verification-token",
            token_type="email_verification",
            expires_at=now + timedelta(hours=24),  # Válido por 24 horas
            created_at=now
        )

        # Verificamos el email
        result = verify_email_uc.execute(verification_token=verification_token)

        # Debería retornar True
        assert result is True

    def test_verify_email_expired_token(self):
        """Test 2: VerifyEmail lanza InvalidVerificationTokenError si el token ha expirado."""
        verify_email_uc = VerifyEmail()

        now = datetime.now(timezone.utc)

        # Creamos un token de verificación expirado
        expired_token = VerificationToken(
            id="token-123",
            user_id="user-123",
            token="email-verification-token",
            token_type="email_verification",
            expires_at=now - timedelta(hours=1),  # Expiró hace 1 hora
            created_at=now - timedelta(hours=25)
        )

        # Intentamos verificar con un token expirado
        with pytest.raises(InvalidVerificationTokenError):
            verify_email_uc.execute(verification_token=expired_token)
