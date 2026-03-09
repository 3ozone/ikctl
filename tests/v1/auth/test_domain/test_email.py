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
        with pytest.raises(Exception):  # FrozenInstanceError en runtime
            setattr(email, "value", "other@example.com")

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

    def test_normalized_returns_lowercase(self):
        """Test 7: normalized() devuelve el email en minúsculas."""
        email = Email("User@Example.COM")
        assert email.normalized() == "user@example.com"

    def test_normalized_already_lowercase(self):
        """Test 8: normalized() no cambia un email ya en minúsculas."""
        email = Email("user@example.com")
        assert email.normalized() == "user@example.com"

    def test_domain_returns_part_after_at(self):
        """Test 9: domain() devuelve la parte del email tras el @."""
        email = Email("user@example.com")
        assert email.domain() == "example.com"

    def test_domain_with_subdomain(self):
        """Test 10: domain() devuelve el dominio completo incluyendo subdominio."""
        email = Email("user@mail.example.com")
        assert email.domain() == "mail.example.com"

    def test_email_whitespace_only_raises_error(self):
        """Test 11: Email con solo espacios lanza InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            Email("   ")

    def test_email_missing_at_sign_raises_error(self):
        """Test 12: Email sin @ lanza InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            Email("userexample.com")

    def test_email_missing_domain_raises_error(self):
        """Test 13: Email sin dominio tras @ lanza InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            Email("user@")

    def test_email_usable_as_dict_key(self):
        """Test 14: Email es hashable y puede usarse como clave de diccionario."""
        email = Email("user@example.com")
        mapping = {email: "value"}
        assert mapping[email] == "value"

    def test_email_usable_in_set(self):
        """Test 15: Dos emails iguales ocupan un solo lugar en un set."""
        email1 = Email("user@example.com")
        email2 = Email("user@example.com")
        result = {email1, email2}
        assert len(result) == 1

    def test_normalized_does_not_mutate_stored_value(self):
        """Test 16: normalized() no altera el valor almacenado en .value."""
        email = Email("User@Example.COM")
        _ = email.normalized()
        assert email.value == "User@Example.COM"
