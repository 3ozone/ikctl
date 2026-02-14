"""Tests para Use Case ResetPassword."""
from datetime import datetime, timezone, timedelta
import pytest

from app.v1.auth.domain.entities import User, VerificationToken
from app.v1.auth.domain.value_objects import Email
from app.v1.auth.domain.exceptions import InvalidVerificationTokenError
from app.v1.auth.use_cases.reset_password import ResetPassword
from app.v1.auth.use_cases.hash_password import HashPassword


class TestResetPassword:
    """Tests del Use Case ResetPassword."""

    def test_reset_password_success(self):
        """Test 1: ResetPassword cambia la contraseña usando un token válido."""
        hash_uc = HashPassword()
        reset_password_uc = ResetPassword(hash_uc)

        user = User(
            id="user-123",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="old_hashed_password",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        now = datetime.now(timezone.utc)
        reset_token = VerificationToken(
            id="token-123",
            user_id=user.id,
            token="reset-token-abc",
            token_type="password_reset",
            expires_at=now + timedelta(hours=24),
            created_at=now
        )

        new_password = "NewSecurePass123"

        # Reseteamos la contraseña
        updated_user = reset_password_uc.execute(
            user=user,
            reset_token=reset_token,
            new_password=new_password
        )

        # Verificamos que la contraseña fue actualizada
        assert isinstance(updated_user, User)
        assert updated_user.id == user.id
        assert updated_user.password_hash != "old_hashed_password"
        assert updated_user.password_hash != new_password  # Está hasheado
        assert len(updated_user.password_hash) > 0

    def test_reset_password_expired_token(self):
        """Test 2: ResetPassword lanza InvalidVerificationTokenError si el token ha expirado."""
        hash_uc = HashPassword()
        reset_password_uc = ResetPassword(hash_uc)

        user = User(
            id="user-123",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="old_hashed_password",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        now = datetime.now(timezone.utc)
        expired_token = VerificationToken(
            id="token-123",
            user_id=user.id,
            token="reset-token-abc",
            token_type="password_reset",
            expires_at=now - timedelta(hours=1),  # Expiró hace 1 hora
            created_at=now - timedelta(hours=25)
        )

        new_password = "NewSecurePass123"

        # Intentamos resetear con un token expirado
        with pytest.raises(InvalidVerificationTokenError):
            reset_password_uc.execute(
                user=user,
                reset_token=expired_token,
                new_password=new_password
            )
