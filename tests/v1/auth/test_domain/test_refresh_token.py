"""Tests para Entity RefreshToken."""
import pytest
from datetime import datetime, timedelta

from app.v1.auth.domain.entities import RefreshToken
from app.v1.auth.domain.exceptions import InvalidRefreshTokenError


class TestRefreshToken:
    """Tests de la Entity RefreshToken."""

    def test_refresh_token_creation(self):
        """Test 1: RefreshToken se crea exitosamente con datos válidos."""
        token_id = "token-123"
        user_id = "user-456"
        token_value = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        expires_at = datetime.now() + timedelta(days=7)

        refresh_token = RefreshToken(
            id=token_id,
            user_id=user_id,
            token=token_value,
            expires_at=expires_at,
            created_at=datetime.now()
        )

        assert refresh_token.id == token_id
        assert refresh_token.user_id == user_id
        assert refresh_token.token == token_value
        assert refresh_token.expires_at == expires_at

    def test_refresh_token_empty_user_id(self):
        """Test 2: RefreshToken con user_id vacío lanza InvalidRefreshTokenError."""
        with pytest.raises(InvalidRefreshTokenError):
            RefreshToken(
                id="token-123",
                user_id="",  # user_id vacío
                token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                expires_at=datetime.now() + timedelta(days=7),
                created_at=datetime.now()
            )

    def test_refresh_token_empty_token(self):
        """Test 3: RefreshToken con token vacío lanza InvalidRefreshTokenError."""
        with pytest.raises(InvalidRefreshTokenError):
            RefreshToken(
                id="token-123",
                user_id="user-456",
                token="",  # token vacío
                expires_at=datetime.now() + timedelta(days=7),
                created_at=datetime.now()
            )

    def test_refresh_token_invalid_expires_at(self):
        """Test 4: RefreshToken con expires_at inválido lanza InvalidRefreshTokenError."""
        with pytest.raises(InvalidRefreshTokenError):
            RefreshToken(
                id="token-123",
                user_id="user-456",
                token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                expires_at="not_a_datetime",  # expires_at inválido
                created_at=datetime.now()
            )

    def test_refresh_token_mutable(self):
        """Test 5: RefreshToken es mutable (sin frozen=True)."""
        refresh_token = RefreshToken(
            id="token-123",
            user_id="user-456",
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            expires_at=datetime.now() + timedelta(days=7),
            created_at=datetime.now()
        )

        # Entities pueden mutar
        new_user_id = "user-999"
        refresh_token.user_id = new_user_id
        assert refresh_token.user_id == new_user_id

    def test_refresh_token_equality(self):
        """Test 6: Dos RefreshTokens con mismo ID son iguales."""
        now = datetime.now()
        expires = now + timedelta(days=7)

        token1 = RefreshToken(
            id="token-123",
            user_id="user-456",
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            expires_at=expires,
            created_at=now
        )
        token2 = RefreshToken(
            id="token-123",
            user_id="user-456",
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            expires_at=expires,
            created_at=now
        )

        assert token1 == token2
