"""Tests para VerificationTokenRepository."""
from datetime import datetime, timezone, timedelta
import pytest

from app.v1.auth.domain.entities import VerificationToken


@pytest.mark.asyncio
async def test_save_verification_token(verification_token_repository):
    """Test 1: Guarda y recupera un token de verificación."""
    token = VerificationToken(
        id="token-123",
        user_id="user-123",
        token="verification-token-abc",
        token_type="email_verification",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        created_at=datetime.now(timezone.utc)
    )

    # Guardar
    saved_token = await verification_token_repository.save(token)
    assert saved_token.id == token.id

    # Recuperar
    found_token = await verification_token_repository.find_by_token("verification-token-abc")
    assert found_token is not None
    assert found_token.user_id == "user-123"
    assert found_token.token_type == "email_verification"


@pytest.mark.asyncio
async def test_find_by_token_not_found(verification_token_repository):
    """Test 2: find_by_token retorna None si no existe."""
    found_token = await verification_token_repository.find_by_token("nonexistent-token")
    assert found_token is None


@pytest.mark.asyncio
async def test_delete_verification_token(verification_token_repository):
    """Test 3: Elimina un token de verificación."""
    token = VerificationToken(
        id="token-456",
        user_id="user-456",
        token="delete-me-token",
        token_type="password_reset",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        created_at=datetime.now(timezone.utc)
    )

    # Guardar
    await verification_token_repository.save(token)

    # Eliminar
    await verification_token_repository.delete("delete-me-token")

    # Verificar que ya no existe
    found_token = await verification_token_repository.find_by_token("delete-me-token")
    assert found_token is None


@pytest.mark.asyncio
async def test_delete_by_user_id_and_type(verification_token_repository):
    """Test 4: Elimina todos los tokens de un tipo para un usuario."""
    user_id = "user-789"

    # Crear varios tokens del mismo tipo
    token1 = VerificationToken(
        id="token-1",
        user_id=user_id,
        token="token-1-abc",
        token_type="email_verification",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        created_at=datetime.now(timezone.utc)
    )
    token2 = VerificationToken(
        id="token-2",
        user_id=user_id,
        token="token-2-def",
        token_type="email_verification",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        created_at=datetime.now(timezone.utc)
    )
    token3 = VerificationToken(
        id="token-3",
        user_id=user_id,
        token="token-3-ghi",
        token_type="password_reset",  # Tipo diferente
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        created_at=datetime.now(timezone.utc)
    )

    await verification_token_repository.save(token1)
    await verification_token_repository.save(token2)
    await verification_token_repository.save(token3)

    # Eliminar solo los de tipo email_verification
    await verification_token_repository.delete_by_user_id(user_id, "email_verification")

    # Verificar que los email_verification fueron eliminados
    assert await verification_token_repository.find_by_token("token-1-abc") is None
    assert await verification_token_repository.find_by_token("token-2-def") is None

    # Verificar que el password_reset sigue existiendo
    found_token3 = await verification_token_repository.find_by_token("token-3-ghi")
    assert found_token3 is not None
    assert found_token3.token_type == "password_reset"
