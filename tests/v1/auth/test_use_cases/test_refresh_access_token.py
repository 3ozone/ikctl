"""Tests para Use Case RefreshAccessToken."""
from datetime import datetime, timezone, timedelta
import pytest

from app.v1.auth.domain.entities import RefreshToken
from app.v1.auth.domain.exceptions import InvalidRefreshTokenError
from app.v1.auth.use_cases.refresh_access_token import RefreshAccessToken
from app.v1.auth.use_cases.create_tokens import CreateTokens
from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email


class TestRefreshAccessToken:
    """Tests del Use Case RefreshAccessToken."""

    def test_refresh_access_token_success(self):
        """Test 1: RefreshAccessToken genera un nuevo access_token usando un refresh_token válido."""
        create_tokens_uc = CreateTokens()
        refresh_uc = RefreshAccessToken()

        # Creamos un usuario y sus tokens
        user = User(
            id="user-123",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hashed_password",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        result = create_tokens_uc.execute(user=user)
        refresh_token = result["refresh_token"]

        # Refrescamos el access token
        new_access_token = refresh_uc.execute(refresh_token=refresh_token)

        # Verificamos que se generó un nuevo token
        assert isinstance(new_access_token, str)
        assert len(new_access_token) > 0
        # El nuevo token debería ser diferente al anterior
        assert new_access_token != result["access_token"]

    def test_refresh_access_token_expired(self):
        """Test 2: RefreshAccessToken lanza InvalidRefreshTokenError si el refresh_token ha expirado."""
        refresh_uc = RefreshAccessToken()

        # Creamos un refresh token expirado (fecha en el pasado)
        now = datetime.now(timezone.utc)
        expired_refresh_token = RefreshToken(
            id="token-123",
            user_id="user-123",
            token="expired-token",
            expires_at=now - timedelta(days=1),  # Expiró hace 1 día
            created_at=now - timedelta(days=7)
        )

        # Intentamos refrescar con un token expirado
        with pytest.raises(InvalidRefreshTokenError):
            refresh_uc.execute(refresh_token=expired_refresh_token)
