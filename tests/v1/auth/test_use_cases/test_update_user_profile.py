"""
Tests para el caso de uso UpdateUserProfile.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest

from app.v1.auth.application.commands.update_user_profile import UpdateUserProfile
from app.v1.auth.application.exceptions import ResourceNotFoundError
from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email


@pytest.mark.asyncio
async def test_update_user_profile_success():
    """Test: Actualizar perfil de usuario exitosamente."""
    # Arrange
    user_repository = AsyncMock()
    existing_user = User(
        id="user-123",
        name="Old Name",
        email=Email("user@example.com"),
        password_hash="hashed_password",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    user_repository.find_by_id.return_value = existing_user
    user_repository.update.return_value = None

    use_case = UpdateUserProfile(user_repository=user_repository)

    # Act
    await use_case.execute(user_id="user-123", new_name="New Name")

    # Assert
    user_repository.find_by_id.assert_called_once_with("user-123")
    user_repository.update.assert_called_once()
    # Verificar que el usuario actualizado tiene el nuevo nombre
    updated_user = user_repository.update.call_args[0][0]
    assert updated_user.name == "New Name"
    assert updated_user.id == "user-123"


@pytest.mark.asyncio
async def test_update_user_profile_user_not_found():
    """Test: Error al actualizar perfil de usuario inexistente."""
    # Arrange
    user_repository = AsyncMock()
    user_repository.find_by_id.return_value = None

    use_case = UpdateUserProfile(user_repository=user_repository)

    # Act & Assert
    with pytest.raises(ResourceNotFoundError, match="no encontrado|not found"):
        await use_case.execute(user_id="user-999", new_name="New Name")

    user_repository.find_by_id.assert_called_once_with("user-999")
    user_repository.update.assert_not_called()
