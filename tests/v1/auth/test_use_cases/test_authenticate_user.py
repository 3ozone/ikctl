"""Tests para Use Case AuthenticateUser."""
from datetime import datetime, timezone
import pytest

from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email
from app.v1.auth.domain.exceptions import InvalidUserError
from app.v1.auth.use_cases.hash_password import HashPassword
from app.v1.auth.use_cases.verify_password import VerifyPassword
from app.v1.auth.use_cases.authenticate_user import AuthenticateUser


class TestAuthenticateUser:
    """Tests del Use Case AuthenticateUser."""

    def test_authenticate_user_success(self):
        """Test 1: AuthenticateUser retorna el usuario si la contraseña es correcta."""
        hash_uc = HashPassword()
        verify_uc = VerifyPassword()
        auth_uc = AuthenticateUser(verify_uc)

        plaintext = "SecurePass123"
        hashed = hash_uc.execute(plaintext)

        # Creamos un usuario con la contraseña hasheada
        user = User(
            id="user-123",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash=hashed,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # Autenticamos con la contraseña correcta
        authenticated_user = auth_uc.execute(
            plaintext_password=plaintext,
            user=user
        )

        assert authenticated_user.id == user.id
        assert authenticated_user.email.value == "john@example.com"

    def test_authenticate_user_wrong_password(self):
        """Test 2: AuthenticateUser lanza InvalidUserError si la contraseña es incorrecta."""
        hash_uc = HashPassword()
        verify_uc = VerifyPassword()
        auth_uc = AuthenticateUser(verify_uc)

        plaintext = "SecurePass123"
        wrong_plaintext = "WrongPass456"
        hashed = hash_uc.execute(plaintext)

        # Creamos un usuario con la contraseña hasheada
        user = User(
            id="user-123",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash=hashed,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # Intentamos autenticar con una contraseña incorrecta
        with pytest.raises(InvalidUserError):
            auth_uc.execute(
                plaintext_password=wrong_plaintext,
                user=user
            )
