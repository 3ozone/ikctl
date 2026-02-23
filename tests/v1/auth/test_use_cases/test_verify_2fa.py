"""
Tests para el caso de uso Verify2FA.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
import pytest

from app.v1.auth.application.use_cases.verify_2fa import Verify2FA
from app.v1.auth.application.exceptions import (
    ResourceNotFoundError,
    UnauthorizedOperationError
)
from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email


@pytest.mark.asyncio
async def test_verify_2fa_success():
    """Test: Verificar código 2FA exitosamente."""
    # Arrange
    user_repository = AsyncMock()
    totp_provider = Mock()

    existing_user = User(
        id="user-123",
        name="Test User",
        email=Email("user@example.com"),
        password_hash="hashed_password",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        totp_secret="BASE32SECRET123",
        is_2fa_enabled=True
    )
    user_repository.find_by_id.return_value = existing_user
    totp_provider.verify_code.return_value = True

    use_case = Verify2FA(
        user_repository=user_repository,
        totp_provider=totp_provider
    )

    # Act
    result = await use_case.execute(user_id="user-123", code="123456")

    # Assert
    user_repository.find_by_id.assert_called_once_with("user-123")
    totp_provider.verify_code.assert_called_once_with(
        secret="BASE32SECRET123",
        code="123456"
    )
    assert result is True


@pytest.mark.asyncio
async def test_verify_2fa_user_not_found():
    """Test: Error al verificar 2FA de usuario inexistente."""
    # Arrange
    user_repository = AsyncMock()
    totp_provider = Mock()

    user_repository.find_by_id.return_value = None

    use_case = Verify2FA(
        user_repository=user_repository,
        totp_provider=totp_provider
    )

    # Act & Assert
    with pytest.raises(ResourceNotFoundError, match="no encontrado|not found"):
        await use_case.execute(user_id="user-999", code="123456")

    user_repository.find_by_id.assert_called_once_with("user-999")
    totp_provider.verify_code.assert_not_called()


@pytest.mark.asyncio
async def test_verify_2fa_not_enabled():
    """Test: Error cuando 2FA no está habilitado."""
    # Arrange
    user_repository = AsyncMock()
    totp_provider = Mock()

    existing_user = User(
        id="user-123",
        name="Test User",
        email=Email("user@example.com"),
        password_hash="hashed_password",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        is_2fa_enabled=False  # 2FA deshabilitado
    )
    user_repository.find_by_id.return_value = existing_user

    use_case = Verify2FA(
        user_repository=user_repository,
        totp_provider=totp_provider
    )

    # Act & Assert
    with pytest.raises(UnauthorizedOperationError, match="2FA no.*habilitado|not enabled"):
        await use_case.execute(user_id="user-123", code="123456")

    user_repository.find_by_id.assert_called_once_with("user-123")
    totp_provider.verify_code.assert_not_called()


@pytest.mark.asyncio
async def test_verify_2fa_invalid_code():
    """Test: Código 2FA inválido."""
    # Arrange
    user_repository = AsyncMock()
    totp_provider = Mock()

    existing_user = User(
        id="user-123",
        name="Test User",
        email=Email("user@example.com"),
        password_hash="hashed_password",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        totp_secret="BASE32SECRET123",
        is_2fa_enabled=True
    )
    user_repository.find_by_id.return_value = existing_user
    totp_provider.verify_code.return_value = False  # Código incorrecto

    use_case = Verify2FA(
        user_repository=user_repository,
        totp_provider=totp_provider
    )

    # Act
    result = await use_case.execute(user_id="user-123", code="999999")

    # Assert
    user_repository.find_by_id.assert_called_once_with("user-123")
    totp_provider.verify_code.assert_called_once_with(
        secret="BASE32SECRET123",
        code="999999"
    )
    assert result is False
