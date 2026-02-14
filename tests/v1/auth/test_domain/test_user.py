"""Tests para Entity User."""
from datetime import datetime
import pytest

from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email
from app.v1.auth.domain.exceptions import InvalidUserError


class TestUser:
    """Tests de la Entity User."""

    def test_user_creation(self):
        """Test 1: User se crea exitosamente con datos válidos."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        name = "John Doe"
        email = Email("john@example.com")
        password_hash = "hashed_password_here"
        now = datetime.now()

        user = User(
            id=user_id,
            name=name,
            email=email,
            password_hash=password_hash,
            created_at=now,
            updated_at=now
        )

        assert user.id == user_id
        assert user.name == name
        assert user.email == email
        assert user.password_hash == password_hash
        assert user.created_at == now
        assert user.updated_at == now

    def test_user_empty_name(self):
        """Test 2: User con name vacío lanza InvalidUserError."""
        with pytest.raises(InvalidUserError):
            User(
                id="123e4567-e89b-12d3-a456-426614174000",
                name="",  # name vacío
                email=Email("john@example.com"),
                password_hash="hashed_password_here",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

    def test_user_empty_id(self):
        """Test 3: User con ID vacío lanza InvalidUserError."""
        with pytest.raises(InvalidUserError):
            User(
                id="",  # id vacío
                name="John Doe",
                email=Email("john@example.com"),
                password_hash="hashed_password_here",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

    def test_user_mutable(self):
        """Test 4: User es mutable (sin frozen=True)."""
        user = User(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hashed_password_here",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Entities pueden mutar (a diferencia de Value Objects)
        new_name = "Jane Doe"
        user.name = new_name
        assert user.name == new_name
