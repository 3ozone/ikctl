"""Tests para Value Object JWT Token."""
from datetime import datetime, timezone
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

    def test_get_user_id_returns_user_id_from_payload(self):
        """Test 8: get_user_id() extrae el user_id del payload."""
        token = JWTToken(
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            payload={"user_id": "abc-123"},
            token_type="access"
        )

        assert token.get_user_id() == "abc-123"

    def test_get_expiration_returns_datetime_from_payload(self):
        """Test 9: get_expiration() extrae el campo exp del payload como datetime UTC."""
        exp_timestamp = 1700000000
        token = JWTToken(
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            payload={"user_id": "123", "exp": exp_timestamp},
            token_type="access"
        )

        result = token.get_expiration()
        assert isinstance(result, datetime)
        assert result == datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

    def test_is_expired_returns_true_when_past(self):
        """Test 10: is_expired() devuelve True cuando el token ha expirado."""
        past_timestamp = 1000000000  # año 2001, claramente pasado
        token = JWTToken(
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            payload={"user_id": "123", "exp": past_timestamp},
            token_type="access"
        )

        assert token.is_expired() is True

    def test_is_expired_returns_false_when_future(self):
        """Test 11: is_expired() devuelve False cuando el token aún es válido."""
        import time
        future_timestamp = int(time.time()) + 3600  # 1 hora en el futuro
        token = JWTToken(
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            payload={"user_id": "123", "exp": future_timestamp},
            token_type="access"
        )

        assert token.is_expired() is False

    def test_is_access_token_returns_true_for_access_type(self):
        """Test 12: is_access_token() devuelve True cuando token_type es 'access'."""
        token = JWTToken(
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            payload={"user_id": "123"},
            token_type="access"
        )

        assert token.is_access_token() is True

    def test_is_access_token_returns_false_for_refresh_type(self):
        """Test 13: is_access_token() devuelve False cuando token_type es 'refresh'."""
        token = JWTToken(
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            payload={"user_id": "123"},
            token_type="refresh"
        )

        assert token.is_access_token() is False

    def test_is_refresh_token_returns_true_for_refresh_type(self):
        """Test 14: is_refresh_token() devuelve True cuando token_type es 'refresh'."""
        token = JWTToken(
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            payload={"user_id": "123"},
            token_type="refresh"
        )

        assert token.is_refresh_token() is True

    def test_is_refresh_token_returns_false_for_access_type(self):
        """Test 15: is_refresh_token() devuelve False cuando token_type es 'access'."""
        token = JWTToken(
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            payload={"user_id": "123"},
            token_type="access"
        )

        assert token.is_refresh_token() is False
