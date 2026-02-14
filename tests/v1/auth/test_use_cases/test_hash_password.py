"""Tests para Use Case HashPassword."""
import pytest

from app.v1.auth.use_cases.hash_password import HashPassword


class TestHashPassword:
    """Tests del Use Case HashPassword."""

    def test_hash_password_success(self):
        """Test 1: HashPassword hasheá una contraseña válida exitosamente."""
        use_case = HashPassword()
        plaintext = "SecurePass123"

        hashed = use_case.execute(plaintext)

        # El hash NO debe ser igual al plaintext
        assert hashed != plaintext
        # El hash debe ser una string
        assert isinstance(hashed, str)
        # El hash debe tener longitud > que el plaintext (bcrypt genera hashes largos)
        assert len(hashed) > len(plaintext)

    def test_hash_password_different_hashes(self):
        """Test 2: Dos hashes de la misma contraseña son diferentes (salt aleatorio)."""
        use_case = HashPassword()
        plaintext = "SecurePass123"

        hash1 = use_case.execute(plaintext)
        hash2 = use_case.execute(plaintext)

        # Aunque plaintext es igual, los hashes son diferentes
        # Porque bcrypt usa salt aleatorio en cada ejecución
        assert hash1 != hash2

    def test_hash_password_returns_bcrypt_format(self):
        """Test 3: El hash retornado tiene formato bcrypt válido."""
        use_case = HashPassword()
        plaintext = "SecurePass123"

        hashed = use_case.execute(plaintext)

        # Bcrypt hashes comienzan con $2y$ o $2b$ (formato)
        assert hashed.startswith('$2')
        # Bcrypt hashes tienen aproximadamente 60 caracteres
        assert len(hashed) == 60
