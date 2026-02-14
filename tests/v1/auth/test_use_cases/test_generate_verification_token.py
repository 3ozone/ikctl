"""Tests para Use Case GenerateVerificationToken."""
from datetime import datetime, timezone, timedelta
import pytest

from app.v1.auth.domain.entities import VerificationToken
from app.v1.auth.use_cases.generate_verification_token import GenerateVerificationToken


class TestGenerateVerificationToken:
    """Tests del Use Case GenerateVerificationToken."""

    def test_generate_verification_token_for_email(self):
        """Test 1: GenerateVerificationToken crea un token de email_verification válido."""
        gen_token_uc = GenerateVerificationToken()

        user_id = "user-123"

        # Generamos un token de verificación de email
        token = gen_token_uc.execute(
            user_id=user_id,
            token_type="email_verification"
        )

        # Verificamos que se creó correctamente
        assert isinstance(token, VerificationToken)
        assert token.user_id == user_id
        assert token.token_type == "email_verification"
        assert token.id is not None
        assert token.token is not None
        assert token.expires_at > datetime.now(timezone.utc)

    def test_generate_verification_token_unique_values(self):
        """Test 2: GenerateVerificationToken genera tokens con valores únicos cada vez."""
        gen_token_uc = GenerateVerificationToken()

        user_id = "user-123"

        # Generamos dos tokens
        token1 = gen_token_uc.execute(
            user_id=user_id,
            token_type="email_verification"
        )
        token2 = gen_token_uc.execute(
            user_id=user_id,
            token_type="email_verification"
        )

        # Verificamos que tienen IDs y tokens únicos
        assert token1.id != token2.id
        assert token1.token != token2.token
        # Ambos pertenecen al mismo usuario
        assert token1.user_id == token2.user_id == user_id
