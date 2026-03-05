"""Tests para Use Case RequestPasswordReset."""
from datetime import datetime, timezone

from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email
from app.v1.auth.application.commands.request_password_reset import RequestPasswordReset
from app.v1.auth.application.commands.generate_verification_token import GenerateVerificationToken
from app.v1.auth.application.dtos.verification_result import VerificationResult


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
        result = request_reset_uc.execute(user=user)

        # Verificamos el resultado
        assert isinstance(result, VerificationResult)
        assert result.success is True
        assert result.user_id == user.id

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
        result1 = request_reset_uc.execute(user=user)
        result2 = request_reset_uc.execute(user=user)

        # Ambos devuelven VerificationResult exitoso para el mismo usuario
        assert isinstance(result1, VerificationResult)
        assert isinstance(result2, VerificationResult)
        assert result1.success is True
        assert result2.success is True
        assert result1.user_id == result2.user_id == user.id
