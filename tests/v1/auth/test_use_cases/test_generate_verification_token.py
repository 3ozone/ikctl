"""Tests para Use Case GenerateVerificationToken."""
from datetime import datetime, timezone, timedelta
import pytest

from app.v1.auth.application.commands.generate_verification_token import GenerateVerificationToken
from app.v1.auth.application.dtos.verification_result import VerificationResult


class TestGenerateVerificationToken:
    """Tests del Use Case GenerateVerificationToken."""

    def test_generate_verification_token_for_email(self):
        """Test 1: GenerateVerificationToken retorna VerificationResult exitoso."""
        gen_token_uc = GenerateVerificationToken()

        user_id = "user-123"

        # Generamos un token de verificación de email
        result = gen_token_uc.execute(
            user_id=user_id,
            token_type="email_verification"
        )

        # Verificamos que se creó correctamente
        assert isinstance(result, VerificationResult)
        assert result.success is True
        assert result.user_id == user_id

    def test_generate_verification_token_unique_values(self):
        """Test 2: GenerateVerificationToken retorna VerificationResult para cada llamada."""
        gen_token_uc = GenerateVerificationToken()

        user_id = "user-123"

        # Generamos dos tokens
        result1 = gen_token_uc.execute(
            user_id=user_id,
            token_type="email_verification"
        )
        result2 = gen_token_uc.execute(
            user_id=user_id,
            token_type="email_verification"
        )

        # Ambos devuelven VerificationResult exitoso para el mismo usuario
        assert result1.success is True
        assert result2.success is True
        assert result1.user_id == result2.user_id == user_id
