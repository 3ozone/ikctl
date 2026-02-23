"""
Tests para RefreshTokenRepository.
"""

from datetime import datetime, timezone, timedelta
import pytest

from app.v1.auth.domain.entities import RefreshToken


@pytest.mark.asyncio
async def test_save_refresh_token(refresh_token_repository):
    """Test: Guardar un refresh token exitosamente."""
    # Arrange
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    token = RefreshToken(
        id="token-123",
        user_id="user-456",
        token="refresh_token_string",
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc)
    )

    # Act
    await refresh_token_repository.save(token)

    # Assert
    found_token = await refresh_token_repository.find_by_token("refresh_token_string")
    assert found_token is not None
    assert found_token.id == "token-123"
    assert found_token.user_id == "user-456"
    assert found_token.token == "refresh_token_string"


@pytest.mark.asyncio
async def test_find_by_token_not_found(refresh_token_repository):
    """Test: Buscar token inexistente retorna None."""
    # Act
    found_token = await refresh_token_repository.find_by_token("nonexistent_token")

    # Assert
    assert found_token is None


@pytest.mark.asyncio
async def test_delete_refresh_token(refresh_token_repository):
    """Test: Eliminar un refresh token."""
    # Arrange
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    token = RefreshToken(
        id="token-789",
        user_id="user-456",
        token="delete_me_token",
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc)
    )
    await refresh_token_repository.save(token)

    # Act
    await refresh_token_repository.delete("delete_me_token")

    # Assert
    found_token = await refresh_token_repository.find_by_token("delete_me_token")
    assert found_token is None
