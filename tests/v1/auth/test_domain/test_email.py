"""Tests para Value Object Email."""
import pytest

from app.v1.auth.domain.value_objects import Email
from app.v1.auth.domain.exceptions import InvalidEmailError


class TestEmail:
    """Tests del Value Object Email."""

    def test_email_valid(self):
        """Test 1: El email válido se crea exitosamente."""
        email = Email("user@example.com")
        assert email.value == "user@example.com"

    def test_email_invalid_format(self):
        """Test 2: El email con formato inválido lanza InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            Email("invalid-email")

    def test_email_empty_string(self):
        """Test 3: Email vacío lanza InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            Email("")

    def test_email_immutable(self):
        """Test 4: Email es inmutable (frozen=True)."""
        email = Email("user@example.com")
        with pytest.raises(Exception):  # FrozenInstanceError
            email.value = "other@example.com"

    def test_email_equality(self):
        """Test 5: Dos emails con mismo valor son iguales."""
        email1 = Email("user@example.com")
        email2 = Email("user@example.com")
        assert email1 == email2

    def test_email_inequality(self):
        """Test 6: Dos emails con diferente valor no son iguales."""
        email1 = Email("user@example.com")
        email2 = Email("other@example.com")
        assert email1 != email2
