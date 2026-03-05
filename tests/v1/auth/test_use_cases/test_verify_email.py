"""Tests para Use Case VerifyEmail."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
import pytest

from app.v1.auth.domain.entities import VerificationToken
from app.v1.auth.domain.exceptions import InvalidVerificationTokenError
from app.v1.auth.application.commands.verify_email import VerifyEmail
from app.v1.auth.domain.events.email_verified import EmailVerified


class TestVerifyEmail:
    """Tests del Use Case VerifyEmail."""

    @pytest.mark.asyncio
    async def test_verify_email_success(self):
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
        result = await verify_email_uc.execute(verification_token=verification_token)

        # Debería retornar True
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_email_expired_token(self):
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
            await verify_email_uc.execute(verification_token=expired_token)

    @pytest.mark.asyncio
    async def test_verify_email_publishes_email_verified_event(self):
        """Test 3: VerifyEmail publica EmailVerified tras verificar el token."""
        event_bus = AsyncMock()
        verify_email_uc = VerifyEmail(event_bus=event_bus)

        now = datetime.now(timezone.utc)
        verification_token = VerificationToken(
            id="token-123",
            user_id="user-123",
            token="email-verification-token",
            token_type="email_verification",
            expires_at=now + timedelta(hours=24),
            created_at=now
        )

        await verify_email_uc.execute(
            verification_token=verification_token,
            user_email="john@example.com"
        )

        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][0]
        assert isinstance(published_event, EmailVerified)
        assert published_event.aggregate_id == "user-123"
        assert published_event.payload["email"] == "john@example.com"
