"""Tests para Use Case RefreshAccessToken."""
from datetime import datetime, timezone, timedelta
import pytest

from app.v1.auth.domain.entities import RefreshToken
from app.v1.auth.domain.exceptions import InvalidRefreshTokenError
from app.v1.auth.application.commands.refresh_access_token import RefreshAccessToken


class TestRefreshAccessToken:
    """Tests del Use Case RefreshAccessToken."""

    def test_refresh_access_token_success(self):
        """Test 1: RefreshAccessToken genera un nuevo access_token usando un refresh_token válido."""
        refresh_uc = RefreshAccessToken()

        # Creamos un RefreshToken entity válido directamente
        now = datetime.now(timezone.utc)
        refresh_token = RefreshToken(
            id="token-123",
            user_id="user-123",
            token="some-opaque-token",
            expires_at=now + timedelta(days=7),
            created_at=now,
        )

        # Refrescamos el access token
        new_access_token = refresh_uc.execute(refresh_token=refresh_token)

        # Verificamos que se generó un nuevo token
        assert isinstance(new_access_token, str)
        assert len(new_access_token) > 0

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
