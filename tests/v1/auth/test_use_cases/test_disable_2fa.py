"""
Tests para el caso de uso Disable2FA.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest

from app.v1.auth.application.commands.disable_2fa import Disable2FA
from app.v1.auth.application.exceptions import ResourceNotFoundError
from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email
from app.v1.auth.domain.events.two_fa_disabled import TwoFADisabled


@pytest.mark.asyncio
async def test_disable_2fa_success():
    """Test: Deshabilitar 2FA exitosamente."""
    # Arrange
    user_repository = AsyncMock()

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
    user_repository.update.return_value = None

    use_case = Disable2FA(user_repository=user_repository)

    # Act
    await use_case.execute(user_id="user-123")

    # Assert
    user_repository.find_by_id.assert_called_once_with("user-123")
    user_repository.update.assert_called_once()

    # Verificar que el usuario fue actualizado sin 2FA
    updated_user = user_repository.update.call_args[0][0]
    assert updated_user.totp_secret is None
    assert updated_user.is_2fa_enabled is False


@pytest.mark.asyncio
async def test_disable_2fa_user_not_found():
    """Test: Error al deshabilitar 2FA de usuario inexistente."""
    # Arrange
    user_repository = AsyncMock()
    user_repository.find_by_id.return_value = None

    use_case = Disable2FA(user_repository=user_repository)

    # Act & Assert
    with pytest.raises(ResourceNotFoundError, match="no encontrado|not found"):
        await use_case.execute(user_id="user-999")

    user_repository.find_by_id.assert_called_once_with("user-999")
    user_repository.update.assert_not_called()


@pytest.mark.asyncio
async def test_disable_2fa_publishes_two_fa_disabled_event():
    """Test: Disable2FA publica TwoFADisabled tras deshabilitar 2FA."""
    user_repository = AsyncMock()
    event_bus = AsyncMock()

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
    user_repository.update.return_value = None

    use_case = Disable2FA(user_repository=user_repository, event_bus=event_bus)

    await use_case.execute(user_id="user-123")

    event_bus.publish.assert_called_once()
    published_event = event_bus.publish.call_args[0][0]
    assert isinstance(published_event, TwoFADisabled)
    assert published_event.aggregate_id == "user-123"
