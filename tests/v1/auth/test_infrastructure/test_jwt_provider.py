"""Tests para PyJWTProvider."""
from datetime import datetime, timezone, timedelta
from jose import jwt
import pytest

from app.v1.auth.domain.value_objects import JWTToken
from app.v1.auth.application.exceptions import InvalidTokenError, TokenExpiredError
from app.v1.auth.infrastructure.adapters.jwt_provider import PyJWTProvider


@pytest.fixture
def jwt_provider():
    """Fixture para PyJWTProvider."""
    # Secret key para tests
    secret_key = "test-secret-key-for-jwt-testing-only"
    algorithm = "HS256"

    return PyJWTProvider(
        secret_key=secret_key,
        algorithm=algorithm,
        access_token_expire_minutes=30,
        refresh_token_expire_days=7
    )


def test_create_access_token(jwt_provider):
    """Test 1: Crea un access token válido."""
    user_id = "user-123"

    token = jwt_provider.create_access_token(user_id)

    assert isinstance(token, JWTToken)
    assert token.token is not None
    assert len(token.token) > 0
    assert token.token_type == "access"


def test_create_access_token_with_additional_claims(jwt_provider):
    """Test 2: Crea access token con claims adicionales."""
    user_id = "user-456"
    additional_claims = {"role": "admin", "email": "admin@example.com"}

    token = jwt_provider.create_access_token(user_id, additional_claims)

    # Decodificar para verificar claims
    payload = jwt_provider.decode_token(token.token)

    assert payload["sub"] == user_id
    assert payload["role"] == "admin"
    assert payload["email"] == "admin@example.com"


def test_create_refresh_token(jwt_provider):
    """Test 3: Crea un refresh token válido."""
    user_id = "user-789"

    token = jwt_provider.create_refresh_token(user_id)

    assert isinstance(token, JWTToken)
    assert token.token is not None
    assert len(token.token) > 0
    assert token.token_type == "refresh"


def test_decode_token_success(jwt_provider):
    """Test 4: Decodifica un token válido."""
    user_id = "user-decode"
    token = jwt_provider.create_access_token(user_id)

    payload = jwt_provider.decode_token(token.token)

    assert payload["sub"] == user_id
    assert "exp" in payload
    assert "iat" in payload


def test_decode_token_invalid(jwt_provider):
    """Test 5: Lanza InvalidTokenError con token inválido."""
    invalid_token = "invalid.token.string"

    with pytest.raises(InvalidTokenError):
        jwt_provider.decode_token(invalid_token)


def test_decode_token_expired(jwt_provider):
    """Test 6: Lanza TokenExpiredError con token expirado."""
    # Crear provider con expiración inmediata para test
    secret_key = "test-secret-key"

    # Crear token ya expirado
    payload = {
        "sub": "user-expired",
        # Expirado hace 10 segundos
        "exp": datetime.now(timezone.utc) - timedelta(seconds=10),
        "iat": datetime.now(timezone.utc) - timedelta(seconds=20)
    }
    expired_token = jwt.encode(payload, secret_key, algorithm="HS256")

    # Usar el mismo secret_key en el provider
    expired_provider = PyJWTProvider(
        secret_key=secret_key,
        algorithm="HS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7
    )

    with pytest.raises(TokenExpiredError):
        expired_provider.decode_token(expired_token)


def test_verify_token_valid(jwt_provider):
    """Test 7: verify_token retorna True para token válido."""
    user_id = "user-verify"
    token = jwt_provider.create_access_token(user_id)

    is_valid = jwt_provider.verify_token(token.token)

    assert is_valid is True


def test_verify_token_invalid(jwt_provider):
    """Test 8: verify_token retorna False para token inválido."""
    invalid_token = "invalid.token.string"

    is_valid = jwt_provider.verify_token(invalid_token)

    assert is_valid is False


def test_access_and_refresh_tokens_different_expiration(jwt_provider):
    """Test 9: Access y refresh tokens tienen diferentes expiraciones."""
    user_id = "user-exp"

    access_token = jwt_provider.create_access_token(user_id)
    refresh_token = jwt_provider.create_refresh_token(user_id)

    # Decodificar ambos tokens
    access_payload = jwt_provider.decode_token(access_token.token)
    refresh_payload = jwt_provider.decode_token(refresh_token.token)

    # Verificar que refresh expira después que access
    assert refresh_payload["exp"] > access_payload["exp"]
