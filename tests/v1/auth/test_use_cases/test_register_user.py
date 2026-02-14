"""Tests para Use Case RegisterUser."""
import pytest

from app.v1.auth.domain.entities import User
from app.v1.auth.domain.exceptions import InvalidEmailError, InvalidUserError
from app.v1.auth.use_cases.hash_password import HashPassword
from app.v1.auth.use_cases.register_user import RegisterUser


class TestRegisterUser:
    """Tests del Use Case RegisterUser."""

    def test_register_user_success(self):
        """Test 1: RegisterUser crea un usuario exitosamente con nombre, email y contraseña hasheada."""
        hash_uc = HashPassword()
        register_uc = RegisterUser()

        plaintext = "SecurePass123"
        hashed = hash_uc.execute(plaintext)

        # Registramos un nuevo usuario
        user = register_uc.execute(
            name="John Doe",
            email="john@example.com",
            password_hash=hashed
        )

        # Verificamos que se creó el usuario correctamente
        assert isinstance(user, User)
        assert user.name == "John Doe"
        assert user.email.value == "john@example.com"
        assert user.password_hash == hashed
        assert user.id is not None

    def test_register_user_invalid_email(self):
        """Test 2: RegisterUser lanza InvalidEmailError si el email es inválido."""
        hash_uc = HashPassword()
        register_uc = RegisterUser()

        plaintext = "SecurePass123"
        hashed = hash_uc.execute(plaintext)

        # Intentamos registrar con un email inválido
        with pytest.raises(InvalidEmailError):
            register_uc.execute(
                name="John Doe",
                email="invalid-email",  # No tiene formato de email
                password_hash=hashed
            )

    def test_register_user_empty_name(self):
        """Test 3: RegisterUser lanza InvalidUserError si el nombre está vacío."""
        hash_uc = HashPassword()
        register_uc = RegisterUser()

        plaintext = "SecurePass123"
        hashed = hash_uc.execute(plaintext)

        # Intentamos registrar con nombre vacío
        with pytest.raises(InvalidUserError):
            register_uc.execute(
                name="",  # Nombre vacío
                email="john@example.com",
                password_hash=hashed
            )
