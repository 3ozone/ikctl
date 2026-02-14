"""Tests para Use Case VerifyAccessToken."""
from datetime import datetime, timezone
import pytest

from app.v1.auth.domain.exceptions import InvalidJWTTokenError
from app.v1.auth.use_cases.verify_access_token import VerifyAccessToken
from app.v1.auth.use_cases.create_tokens import CreateTokens
from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email


class TestVerifyAccessToken:
    """Tests del Use Case VerifyAccessToken."""

    def test_verify_access_token_success(self):
        """Test 1: VerifyAccessToken verifica un JWT válido y retorna el payload."""
        create_tokens_uc = CreateTokens()
        verify_token_uc = VerifyAccessToken()

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
        access_token = result["access_token"]

        # Verificamos el access token
        payload = verify_token_uc.execute(access_token=access_token)

        # Verificamos que el payload contiene los datos esperados
        assert payload["sub"] == user.id
        assert payload["email"] == "john@example.com"
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_access_token_invalid_token(self):
        """Test 2: VerifyAccessToken lanza InvalidJWTTokenError si el token es inválido."""
        verify_token_uc = VerifyAccessToken()

        # Intentamos verificar con un token inválido
        invalid_token = "invalid.token.here"

        with pytest.raises(InvalidJWTTokenError):
            verify_token_uc.execute(access_token=invalid_token)
