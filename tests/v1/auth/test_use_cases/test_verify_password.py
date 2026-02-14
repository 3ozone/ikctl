"""Tests para Use Case VerifyPassword."""
import pytest

from app.v1.auth.use_cases.hash_password import HashPassword
from app.v1.auth.use_cases.verify_password import VerifyPassword


class TestVerifyPassword:
    """Tests del Use Case VerifyPassword."""

    def test_verify_password_correct(self):
        """Test 1: VerifyPassword retorna True para contraseña correcta."""
        hash_uc = HashPassword()
        verify_uc = VerifyPassword()

        plaintext = "SecurePass123"
        # Primero hasheamos la contraseña
        hashed = hash_uc.execute(plaintext)

        # Luego verificamos que el plaintext coincide con el hash
        result = verify_uc.execute(plaintext, hashed)

        assert result is True

    def test_verify_password_incorrect(self):
        """Test 2: VerifyPassword retorna False para contraseña incorrecta."""
        hash_uc = HashPassword()
        verify_uc = VerifyPassword()

        plaintext = "SecurePass123"
        wrong_plaintext = "WrongPass456"

        # Hasheamos el plaintext correcto
        hashed = hash_uc.execute(plaintext)

        # Intentamos verificar con una contraseña diferente
        result = verify_uc.execute(wrong_plaintext, hashed)

        assert result is False

    def test_verify_password_with_tampered_hash(self):
        """Test 3: VerifyPassword retorna False si el hash fue modificado."""
        hash_uc = HashPassword()
        verify_uc = VerifyPassword()

        plaintext = "SecurePass123"

        # Hasheamos la contraseña
        hashed = hash_uc.execute(plaintext)

        # Modificamos un carácter del hash (simulando corrupción)
        tampered_hash = hashed[:-1] + ("X" if hashed[-1] != "X" else "Y")

        # Intentamos verificar con el hash modificado
        result = verify_uc.execute(plaintext, tampered_hash)

        assert result is False
