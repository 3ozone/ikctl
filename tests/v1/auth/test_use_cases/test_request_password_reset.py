"""Tests para Use Case RequestPasswordReset."""
from datetime import datetime, timezone

from app.v1.auth.domain.entities import VerificationToken, User
from app.v1.auth.domain.value_objects import Email
from app.v1.auth.use_cases.request_password_reset import RequestPasswordReset
from app.v1.auth.use_cases.generate_verification_token import GenerateVerificationToken


class TestRequestPasswordReset:
    """Tests del Use Case RequestPasswordReset."""

    def test_request_password_reset_success(self):
        """Test 1: RequestPasswordReset genera un token de password_reset para un usuario."""
        gen_token_uc = GenerateVerificationToken()
        request_reset_uc = RequestPasswordReset(gen_token_uc)

        user = User(
            id="user-123",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hashed_password",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # Solicitamos reset de contraseña
        reset_token = request_reset_uc.execute(user=user)

        # Verificamos que se generó el token correctamente
        assert isinstance(reset_token, VerificationToken)
        assert reset_token.user_id == user.id
        assert reset_token.token_type == "password_reset"
        assert reset_token.id is not None
        assert reset_token.token is not None
        assert reset_token.expires_at > datetime.now(timezone.utc)

    def test_request_password_reset_unique_tokens(self):
        """Test 2: RequestPasswordReset genera tokens únicos cada vez que se solicita."""
        gen_token_uc = GenerateVerificationToken()
        request_reset_uc = RequestPasswordReset(gen_token_uc)

        user = User(
            id="user-123",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hashed_password",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # Solicitamos dos reseteos de contraseña
        token1 = request_reset_uc.execute(user=user)
        token2 = request_reset_uc.execute(user=user)

        # Verificamos que los tokens sean únicos
        assert token1.id != token2.id
        assert token1.token != token2.token
        # Pero pertenecen al mismo usuario
        assert token1.user_id == token2.user_id == user.id
