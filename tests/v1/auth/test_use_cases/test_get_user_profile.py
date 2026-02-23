"""Tests para Use Case GetUserProfile."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest

from app.v1.auth.domain.value_objects import Email
from app.v1.auth.domain.entities import User
from app.v1.auth.application.use_cases.get_user_profile import GetUserProfile
from app.v1.auth.application.dtos.user_profile import UserProfile
from app.v1.auth.application.exceptions import ResourceNotFoundError


class TestGetUserProfile:
    """Tests del Use Case GetUserProfile."""

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self):
        """Test 1: GetUserProfile retorna UserProfile cuando el usuario existe."""
        # Mock del user repository
        mock_user_repo = AsyncMock()

        # Usuario existente
        user = User(
            id="user-123",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="$2b$12$hash",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 15, tzinfo=timezone.utc)
        )
        mock_user_repo.find_by_id.return_value = user

        get_user_profile_uc = GetUserProfile(mock_user_repo)

        # ACT
        profile = await get_user_profile_uc.execute("user-123")

        # ASSERT
        assert isinstance(profile, UserProfile)
        assert profile.id == "user-123"
        assert profile.name == "John Doe"
        assert profile.email == "john@example.com"
        assert profile.is_verified is False
        assert profile.is_2fa_enabled is False
        assert profile.created_at == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert profile.updated_at == datetime(2024, 1, 15, tzinfo=timezone.utc)

        # Verificar que se llamó al repositorio
        mock_user_repo.find_by_id.assert_called_once_with("user-123")

    @pytest.mark.asyncio
    async def test_get_user_profile_user_not_found(self):
        """Test 2: GetUserProfile lanza ResourceNotFoundError cuando el usuario no existe."""
        # Mock del user repository que retorna None
        mock_user_repo = AsyncMock()
        mock_user_repo.find_by_id.return_value = None

        get_user_profile_uc = GetUserProfile(mock_user_repo)

        # ACT & ASSERT
        with pytest.raises(ResourceNotFoundError, match="no encontrado|not found"):
            await get_user_profile_uc.execute("user-999")

        # Verificar que se intentó buscar
        mock_user_repo.find_by_id.assert_called_once_with("user-999")
