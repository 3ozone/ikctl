"""Tests para AiosmtplibEmailService."""
from unittest.mock import AsyncMock, patch
import pytest

from app.v1.auth.infrastructure.adapters.email_service import AiosmtplibEmailService
from app.v1.auth.infrastructure.exceptions import EmailServiceError


@pytest.fixture
def email_service():
    """Fixture para AiosmtplibEmailService con configuración de test."""
    return AiosmtplibEmailService(
        smtp_host="smtp.test.com",
        smtp_port=587,
        smtp_user="test@example.com",
        smtp_password="test_password",
        from_email="noreply@ikctl.com",
        from_name="ikctl Test",
        base_url="http://localhost:3000"
    )


@pytest.mark.asyncio
async def test_send_verification_email_success(email_service):
    """Test 1: Envía email de verificación exitosamente."""
    with patch('aiosmtplib.SMTP') as mock_smtp:
        # Configurar mock
        mock_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_instance
        mock_instance.send_message = AsyncMock()

        # Ejecutar
        await email_service.send_verification_email(
            to_email="user@example.com",
            token="verification-token-123",
            user_name="John Doe"
        )

        # Verificar que se llamó send_message
        assert mock_instance.send_message.called


@pytest.mark.asyncio
async def test_send_verification_email_contains_token(email_service):
    """Test 2: Email de verificación contiene el token en el link."""
    with patch('aiosmtplib.SMTP') as mock_smtp:
        mock_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_instance

        captured_message = None

        async def capture_message(msg):
            nonlocal captured_message
            captured_message = msg

        mock_instance.send_message = AsyncMock(side_effect=capture_message)

        await email_service.send_verification_email(
            to_email="user@example.com",
            token="test-token-456",
            user_name="Jane"
        )

        # Verificar que el mensaje contiene el token
        assert captured_message is not None
        message_body = captured_message.get_payload(
            decode=True).decode('utf-8')  # type: ignore
        assert "test-token-456" in message_body


@pytest.mark.asyncio
async def test_send_password_reset_email_success(email_service):
    """Test 3: Envía email de reset de contraseña exitosamente."""
    with patch('aiosmtplib.SMTP') as mock_smtp:
        mock_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_instance
        mock_instance.send_message = AsyncMock()

        await email_service.send_password_reset_email(
            to_email="user@example.com",
            token="reset-token-789",
            user_name="Alice"
        )

        assert mock_instance.send_message.called


@pytest.mark.asyncio
async def test_send_password_reset_email_contains_token(email_service):
    """Test 4: Email de reset contiene el token en el link."""
    with patch('aiosmtplib.SMTP') as mock_smtp:
        mock_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_instance

        captured_message = None

        async def capture_message(msg):
            nonlocal captured_message
            captured_message = msg

        mock_instance.send_message = AsyncMock(side_effect=capture_message)

        await email_service.send_password_reset_email(
            to_email="reset@example.com",
            token="reset-abc-123",
            user_name="Bob"
        )

        message_body = captured_message.get_payload(
            decode=True).decode('utf-8')  # type: ignore
        assert "reset-abc-123" in message_body


@pytest.mark.asyncio
async def test_send_password_changed_notification_success(email_service):
    """Test 5: Envía notificación de cambio de contraseña."""
    with patch('aiosmtplib.SMTP') as mock_smtp:
        mock_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_instance
        mock_instance.send_message = AsyncMock()

        await email_service.send_password_changed_notification(
            to_email="user@example.com",
            user_name="Charlie"
        )

        assert mock_instance.send_message.called


@pytest.mark.asyncio
async def test_send_2fa_enabled_notification_success(email_service):
    """Test 6: Envía notificación de activación de 2FA."""
    with patch('aiosmtplib.SMTP') as mock_smtp:
        mock_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_instance
        mock_instance.send_message = AsyncMock()

        await email_service.send_2fa_enabled_notification(
            to_email="user@example.com",
            user_name="David"
        )

        assert mock_instance.send_message.called


@pytest.mark.asyncio
async def test_send_email_smtp_error_raises_exception(email_service):
    """Test 7: Error SMTP lanza EmailServiceError."""
    with patch('aiosmtplib.SMTP') as mock_smtp:
        mock_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_instance
        mock_instance.send_message = AsyncMock(
            side_effect=Exception("SMTP connection failed"))

        with pytest.raises(EmailServiceError) as exc_info:
            await email_service.send_verification_email(
                to_email="fail@example.com",
                token="token",
                user_name="Test"
            )

        assert "error enviando email de verificación" in str(
            exc_info.value).lower()


@pytest.mark.asyncio
async def test_emails_contain_user_name(email_service):
    """Test 8: Todos los emails contienen el nombre del usuario."""
    with patch('aiosmtplib.SMTP') as mock_smtp:
        mock_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_instance

        messages = []

        async def capture_message(msg):
            messages.append(msg)

        mock_instance.send_message = AsyncMock(side_effect=capture_message)

        user_name = "TestUser123"

        # Enviar cada tipo de email
        await email_service.send_verification_email("a@test.com", "token1", user_name)
        await email_service.send_password_reset_email("b@test.com", "token2", user_name)
        await email_service.send_password_changed_notification("c@test.com", user_name)
        await email_service.send_2fa_enabled_notification("d@test.com", user_name)

        # Verificar que todos contienen el nombre
        assert len(messages) == 4
        for message in messages:
            message_body = message.get_payload(
                decode=True).decode('utf-8')  # type: ignore
            assert user_name in message_body
