"""
Tests para el caso de uso Enable2FA.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
import pytest

from app.v1.auth.application.use_cases.enable_2fa import Enable2FA
from app.v1.auth.application.exceptions import ResourceNotFoundError
from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email


@pytest.mark.asyncio
async def test_enable_2fa_success():
    """Test: Habilitar 2FA exitosamente."""
    # Arrange
    user_repository = AsyncMock()
    totp_provider = Mock()

    existing_user = User(
        id="user-123",
        name="Test User",
        email=Email("user@example.com"),
        password_hash="hashed_password",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    user_repository.find_by_id.return_value = existing_user
    user_repository.update.return_value = None

    totp_provider.generate_secret.return_value = "BASE32SECRET123"
    totp_provider.generate_qr_code.return_value = "data:image/png;base64,iVBORw0KG..."

    use_case = Enable2FA(
        user_repository=user_repository,
        totp_provider=totp_provider
    )

    # Act
    result = await use_case.execute(user_id="user-123")

    # Assert
    user_repository.find_by_id.assert_called_once_with("user-123")
    totp_provider.generate_secret.assert_called_once()
    totp_provider.generate_qr_code.assert_called_once_with(
        secret="BASE32SECRET123",
        user_email="user@example.com",
        issuer="ikctl"
    )
    user_repository.update.assert_called_once()

    # Verificar el resultado contiene secret y qr_code
    assert result["secret"] == "BASE32SECRET123"
    assert result["qr_code"] == "data:image/png;base64,iVBORw0KG..."

    # Verificar que el usuario fue actualizado con el secret
    updated_user = user_repository.update.call_args[0][0]
    assert updated_user.totp_secret == "BASE32SECRET123"
    assert updated_user.is_2fa_enabled is True


@pytest.mark.asyncio
async def test_enable_2fa_user_not_found():
    """Test: Error al habilitar 2FA para usuario inexistente."""
    # Arrange
    user_repository = AsyncMock()
    totp_provider = Mock()

    user_repository.find_by_id.return_value = None

    use_case = Enable2FA(
        user_repository=user_repository,
        totp_provider=totp_provider
    )

    # Act & Assert
    with pytest.raises(ResourceNotFoundError, match="no encontrado|not found"):
        await use_case.execute(user_id="user-999")

    user_repository.find_by_id.assert_called_once_with("user-999")
    totp_provider.generate_secret.assert_not_called()
    totp_provider.generate_qr_code.assert_not_called()
    user_repository.update.assert_not_called()
