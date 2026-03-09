"""Tests para Value Object Password."""
import pytest

from app.v1.auth.domain.value_objects import Password
from app.v1.auth.domain.exceptions import InvalidPasswordError


class TestPassword:
    """Tests del Value Object Password."""

    def test_password_valid(self):
        """Test 1: El password válido se crea exitosamente."""
        password = Password("SecurePass123")
        assert password.value == "SecurePass123"

    def test_password_too_short(self):
        """Test 2: Password muy corto lanza InvalidPasswordError."""
        with pytest.raises(InvalidPasswordError):
            Password("Short1A")  # 7 caracteres, falta 1

    def test_password_no_uppercase(self):
        """Test 3: Password sin mayúscula lanza InvalidPasswordError."""
        with pytest.raises(InvalidPasswordError):
            Password("lowercasepassword123")

    def test_password_no_lowercase(self):
        """Test 4: Password sin minúscula lanza InvalidPasswordError."""
        with pytest.raises(InvalidPasswordError):
            Password("UPPERCASEPASSWORD123")

    def test_password_no_digit(self):
        """Test 5: Password sin dígito lanza InvalidPasswordError."""
        with pytest.raises(InvalidPasswordError):
            Password("NoDigitsHere")

    def test_password_immutable(self):
        """Test 6: Password es inmutable (frozen=True)."""
        password = Password("SecurePass123")
        with pytest.raises(Exception):  # FrozenInstanceError en runtime
            setattr(password, "value", "OtherPass123")

    def test_password_equality(self):
        """Test 7: Dos passwords iguales son iguales."""
        pwd1 = Password("SecurePass123")
        pwd2 = Password("SecurePass123")
        assert pwd1 == pwd2

    def test_password_inequality(self):
        """Test 8: Dos passwords diferentes no son iguales."""
        pwd1 = Password("SecurePass123")
        pwd2 = Password("OtherPass123")
        assert pwd1 != pwd2

    def test_password_exactly_minimum_length_is_valid(self):
        """Test 9: Password de exactamente 8 caracteres (límite mínimo) es válido."""
        password = Password("Secure1A")  # exactamente 8 chars
        assert password.value == "Secure1A"

    def test_password_empty_string_raises_error(self):
        """Test 10: Password vacío lanza InvalidPasswordError."""
        with pytest.raises(InvalidPasswordError):
            Password("")

    def test_password_one_char_below_minimum_raises_error(self):
        """Test 11: Password de 7 caracteres (un menos del mínimo) lanza InvalidPasswordError."""
        with pytest.raises(InvalidPasswordError):
            Password("Sec1234")  # 7 chars

    def test_password_usable_as_dict_key(self):
        """Test 12: Password es hashable y puede usarse como clave de diccionario."""
        pwd = Password("SecurePass123")
        mapping = {pwd: True}
        assert mapping[pwd] is True
