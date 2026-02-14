"""Tests para Use Case RevokeRefreshToken."""
from datetime import datetime, timezone, timedelta
import pytest

from app.v1.auth.domain.entities import RefreshToken
from app.v1.auth.domain.exceptions import InvalidRefreshTokenError
from app.v1.auth.use_cases.revoke_refresh_token import RevokeRefreshToken
from app.v1.auth.use_cases.refresh_access_token import RefreshAccessToken


class TestRevokeRefreshToken:
    """Tests del Use Case RevokeRefreshToken."""

    def test_revoke_refresh_token_success(self):
        """Test 1: RevokeRefreshToken marca un refresh_token como revocado."""
        revoke_uc = RevokeRefreshToken()

        now = datetime.now(timezone.utc)
        refresh_token = RefreshToken(
            id="token-123",
            user_id="user-123",
            token="refresh-token-abc",
            expires_at=now + timedelta(days=7),
            created_at=now
        )

        # Revocamos el token
        revoked_token = revoke_uc.execute(refresh_token=refresh_token)

        # Verificamos que el token fue modificado
        assert isinstance(revoked_token, RefreshToken)
        assert revoked_token.id == refresh_token.id
        # El token debería expirar inmediatamente
        assert revoked_token.expires_at <= datetime.now(timezone.utc)

    def test_revoke_refresh_token_cannot_refresh_after_revocation(self):
        """Test 2: Un refresh_token revocado no puede ser usado para refrescar."""
        revoke_uc = RevokeRefreshToken()
        refresh_uc = RefreshAccessToken()

        now = datetime.now(timezone.utc)
        valid_token = RefreshToken(
            id="token-123",
            user_id="user-123",
            token="refresh-token-abc",
            expires_at=now + timedelta(days=7),
            created_at=now
        )

        # Revocamos el token
        revoked_token = revoke_uc.execute(refresh_token=valid_token)

        # Intentamos usar el token revocado para refrescar acceso
        with pytest.raises(InvalidRefreshTokenError):
            refresh_uc.execute(refresh_token=revoked_token)
