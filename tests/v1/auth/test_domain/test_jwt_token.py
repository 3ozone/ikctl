"""Tests para Value Object JWT Token."""
import pytest
from typing import Dict, Any

from app.v1.auth.domain.value_objects import JWTToken
from app.v1.auth.domain.exceptions import InvalidJWTTokenError


class TestJWTToken:
    """Tests del Value Object JWTToken."""

    def test_jwt_token_creation(self):
        """Test 1: JWT Token válido se crea exitosamente."""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        payload = {"user_id": "123", "type": "access"}

        jwt_token = JWTToken(
            token=token,
            payload=payload,
            token_type="access"
        )

        assert jwt_token.token == token
        assert jwt_token.payload == payload
        assert jwt_token.token_type == "access"

    def test_jwt_token_invalid_type(self):
        """Test 2: JWT Token con tipo inválido lanza InvalidJWTTokenError."""
        with pytest.raises(InvalidJWTTokenError):
            JWTToken(
                token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                payload={"user_id": "123"},
                token_type="invalid_type"  # Solo acepta "access" o "refresh"
            )

    def test_jwt_token_empty_token(self):
        """Test 3: JWT Token vacío lanza InvalidJWTTokenError."""
        with pytest.raises(InvalidJWTTokenError):
            JWTToken(
                token="",  # token vacío
                payload={"user_id": "123"},
                token_type="access"
            )

    def test_jwt_token_empty_payload(self):
        """Test 4: JWT Token con payload vacío lanza InvalidJWTTokenError."""
        with pytest.raises(InvalidJWTTokenError):
            JWTToken(
                token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                payload={},  # payload vacío
                token_type="access"
            )

    def test_jwt_token_immutable(self):
        """Test 5: JWT Token es inmutable (frozen=True)."""
        jwt_token = JWTToken(
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            payload={"user_id": "123"},
            token_type="access"
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            jwt_token.token = "new_token"

    def test_jwt_token_equality(self):
        """Test 6: Dos JWT Tokens con mismos valores son iguales."""
        payload = {"user_id": "123"}
        token1 = JWTToken(
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            payload=payload,
            token_type="access"
        )
        token2 = JWTToken(
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            payload=payload,
            token_type="access"
        )

        assert token1 == token2

    def test_jwt_token_inequality(self):
        """Test 7: Dos JWT Tokens con diferentes valores no son iguales."""
        token1 = JWTToken(
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            payload={"user_id": "123"},
            token_type="access"
        )
        token2 = JWTToken(
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            payload={"user_id": "456"},
            token_type="refresh"
        )

        assert token1 != token2
