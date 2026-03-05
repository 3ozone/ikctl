"""Tests para Use Case RegisterUser."""
import pytest
from unittest.mock import AsyncMock

from app.v1.auth.domain.exceptions import InvalidEmailError, InvalidUserError
from app.v1.auth.application.dtos.registration_result import RegistrationResult
from app.v1.auth.application.queries.hash_password import HashPassword
from app.v1.auth.application.commands.register_user import RegisterUser
from app.v1.auth.domain.events.user_registered import UserRegistered


class TestRegisterUser:
    """Tests del Use Case RegisterUser."""

    @pytest.mark.asyncio
    async def test_register_user_success(self):
        """Test 1: RegisterUser devuelve RegistrationResult con datos del usuario creado."""
        hash_uc = HashPassword()
        register_uc = RegisterUser()

        plaintext = "SecurePass123"
        hashed = hash_uc.execute(plaintext)

        result = await register_uc.execute(
            name="John Doe",
            email="john@example.com",
            password_hash=hashed
        )

        assert isinstance(result, RegistrationResult)
        assert result.user_id is not None
        assert result.email == "john@example.com"
        assert result.verification_token_sent is False

    @pytest.mark.asyncio
    async def test_register_user_invalid_email(self):
        """Test 2: RegisterUser lanza InvalidEmailError si el email es inválido."""
        hash_uc = HashPassword()
        register_uc = RegisterUser()

        plaintext = "SecurePass123"
        hashed = hash_uc.execute(plaintext)

        # Intentamos registrar con un email inválido
        with pytest.raises(InvalidEmailError):
            await register_uc.execute(
                name="John Doe",
                email="invalid-email",  # No tiene formato de email
                password_hash=hashed
            )

    @pytest.mark.asyncio
    async def test_register_user_empty_name(self):
        """Test 3: RegisterUser lanza InvalidUserError si el nombre está vacío."""
        hash_uc = HashPassword()
        register_uc = RegisterUser()

        plaintext = "SecurePass123"
        hashed = hash_uc.execute(plaintext)

        # Intentamos registrar con nombre vacío
        with pytest.raises(InvalidUserError):
            await register_uc.execute(
                name="",  # Nombre vacío
                email="john@example.com",
                password_hash=hashed
            )

    @pytest.mark.asyncio
    async def test_register_user_publishes_user_registered_event(self):
        """Test 4: RegisterUser publica UserRegistered tras crear el usuario."""
        hash_uc = HashPassword()
        event_bus = AsyncMock()
        register_uc = RegisterUser(event_bus=event_bus)

        hashed = hash_uc.execute("SecurePass123")
        result = await register_uc.execute(
            name="John Doe",
            email="john@example.com",
            password_hash=hashed
        )

        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][0]
        assert isinstance(published_event, UserRegistered)
        assert published_event.aggregate_id == result.user_id
        assert published_event.payload["email"] == "john@example.com"
