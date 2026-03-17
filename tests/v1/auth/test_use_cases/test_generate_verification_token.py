"""Tests para Use Case GenerateVerificationToken."""
from unittest.mock import AsyncMock
import pytest

from app.v1.auth.application.commands.generate_verification_token import GenerateVerificationToken
from app.v1.auth.application.dtos.verification_result import VerificationResult
from app.v1.auth.domain.entities import VerificationToken


class TestGenerateVerificationToken:
    """Tests del Use Case GenerateVerificationToken."""

    @pytest.mark.asyncio
    async def test_generate_verification_token_for_email(self):
        """Test 1: GenerateVerificationToken retorna VerificationResult exitoso."""
        gen_token_uc = GenerateVerificationToken()

        user_id = "user-123"

        # Generamos un token de verificación de email
        result = await gen_token_uc.execute(
            user_id=user_id,
            token_type="email_verification"
        )

        # Verificamos que se creó correctamente
        assert isinstance(result, VerificationResult)
        assert result.success is True
        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_generate_verification_token_unique_values(self):
        """Test 2: GenerateVerificationToken retorna VerificationResult para cada llamada."""
        gen_token_uc = GenerateVerificationToken()

        user_id = "user-123"

        # Generamos dos tokens
        result1 = await gen_token_uc.execute(
            user_id=user_id,
            token_type="email_verification"
        )
        result2 = await gen_token_uc.execute(
            user_id=user_id,
            token_type="email_verification"
        )

        # Ambos devuelven VerificationResult exitoso para el mismo usuario
        assert result1.success is True
        assert result2.success is True
        assert result1.user_id == result2.user_id == user_id

    @pytest.mark.asyncio
    async def test_generate_verification_token_persists_token(self):
        """Test 3: GenerateVerificationToken llama a repository.save() con el VerificationToken."""
        repo = AsyncMock()
        repo.save = AsyncMock(side_effect=lambda t: t)
        gen_token_uc = GenerateVerificationToken(
            verification_token_repository=repo)

        await gen_token_uc.execute(user_id="user-456", token_type="email_verification")

        repo.save.assert_called_once()
        saved_token = repo.save.call_args[0][0]
        assert isinstance(saved_token, VerificationToken)
        assert saved_token.user_id == "user-456"
        assert saved_token.token_type == "email_verification"

    @pytest.mark.asyncio
    async def test_generate_verification_token_returns_token_value(self):
        """Test 4: GenerateVerificationToken devuelve el valor del token en el resultado."""
        repo = AsyncMock()
        repo.save = AsyncMock(side_effect=lambda t: t)
        gen_token_uc = GenerateVerificationToken(
            verification_token_repository=repo)

        result = await gen_token_uc.execute(user_id="user-789", token_type="email_verification")

        assert result.success is True
        assert result.user_id == "user-789"
        assert result.token is not None
        assert len(result.token) > 0
