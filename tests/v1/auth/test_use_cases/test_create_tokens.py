"""Tests para Use Case CreateTokens."""
from datetime import datetime, timezone, timedelta
from jose import jwt

from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email
from app.v1.auth.application.dtos.token_pair import TokenPair
from app.v1.auth.application.commands.create_tokens import CreateTokens


class TestCreateTokens:
    """Tests del Use Case CreateTokens."""

    def test_create_tokens_success(self):
        """Test 1: CreateTokens crea access_token y refresh_token exitosamente."""
        create_tokens_uc = CreateTokens()

        # Creamos un usuario
        user = User(
            id="user-123",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hashed_password",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # Creamos los tokens
        result = create_tokens_uc.execute(user=user)

        assert isinstance(result, TokenPair)
        assert isinstance(result.access_token, str)
        assert len(result.access_token) > 0
        assert isinstance(result.refresh_token, str)
        assert len(result.refresh_token) > 0
        assert result.token_type == "Bearer"

    def test_create_tokens_expiration_times(self):
        """Test 2: CreateTokens establece los tiempos de expiración correctamente."""
        create_tokens_uc = CreateTokens()

        # Creamos un usuario
        user = User(
            id="user-123",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hashed_password",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        before = datetime.now(timezone.utc)
        result = create_tokens_uc.execute(user=user)

        payload = jwt.get_unverified_claims(result.access_token)
        access_token_exp = datetime.fromtimestamp(payload["exp"], timezone.utc)

        expected_access_exp = before + timedelta(minutes=30)
        time_diff = abs(
            (access_token_exp - expected_access_exp).total_seconds())
        assert time_diff < 60

        expected_refresh_exp = before + timedelta(days=7)
        time_diff = abs((result.refresh_expires_at -
                        expected_refresh_exp).total_seconds())
        assert time_diff < 60
