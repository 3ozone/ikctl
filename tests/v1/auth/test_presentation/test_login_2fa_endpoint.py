"""Tests de integración — Login 2FA (T-40).

T-40: POST /api/v1/auth/login/2fa
    — Verifica el código TOTP tras login con requires_2fa=True.
    — Devuelve tokens si el código es válido.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.value_objects.email import Email
from app.v1.auth.infrastructure.presentation.deps import (
    get_event_bus,
    get_jwt_provider,
    get_refresh_token_repository,
    get_totp_provider,
    get_user_repository,
)
from main import app  # noqa: E402
from tests.v1.auth.test_presentation.conftest import (
    FakeEventBus,
    FakeRefreshTokenRepository,
    FakeUserRepository,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-2fa-1"
_USER_EMAIL = "twofa@example.com"
_TOTP_SECRET = "TOTP_SECRET_FOR_TESTS"
_VALID_CODE = "123456"
_INVALID_CODE = "000000"
_TEMP_TOKEN = "fake-temp-token-for-2fa"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_2fa_user() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=_USER_ID,
        name="Two FA User",
        email=Email(_USER_EMAIL),
        password_hash="hashed-password",
        totp_secret=_TOTP_SECRET,
        is_2fa_enabled=True,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Fakes específicos de 2FA
# ---------------------------------------------------------------------------

class FakeTOTPProvider:
    """Fake en memoria para TOTPProvider."""

    def __init__(self, valid: bool = True) -> None:
        self._valid = valid

    def generate_secret(self) -> str:
        """Fake — retorna secret predecible."""
        return _TOTP_SECRET

    def get_provisioning_uri(self, secret: str, email: str) -> str:  # noqa: ARG002
        """Fake — retorna URI predecible."""
        return f"otpauth://totp/ikctl:{email}?secret={secret}"

    def verify_code(self, secret: str, code: str) -> bool:  # noqa: ARG002
        """Fake — retorna el valor configurado en __init__."""
        return self._valid


class FakeJWTProvider:
    """Fake en memoria para JWTProvider (T-40)."""

    def create_access_token(self, user_id: str, **_kwargs) -> object:
        """Fake — retorna token con valor predecible."""
        class _Token:
            token = f"fake-access-token-{user_id}"
        return _Token()

    def create_refresh_token(self, user_id: str, **_kwargs) -> object:
        """Fake — retorna refresh token con valor predecible."""
        class _Token:
            token = f"fake-refresh-token-{user_id}"
        return _Token()

    def decode_token(self, token: str) -> dict:  # noqa: ARG002
        """Fake — retorna payload con user_id fijo."""
        return {"sub": _USER_ID}

    def verify_token(self, token: str) -> bool:  # noqa: ARG002
        """Fake — siempre retorna True."""
        return True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="client_2fa_valid")
def fixture_client_2fa_valid():
    """Cliente con TOTP válido y usuario con 2FA activo."""
    user = _make_2fa_user()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(user=user)  # noqa: SIM901
    app.dependency_overrides[get_refresh_token_repository] = lambda: FakeRefreshTokenRepository()  # noqa: SIM901
    app.dependency_overrides[get_totp_provider] = lambda: FakeTOTPProvider(valid=True)  # noqa: SIM901
    app.dependency_overrides[get_jwt_provider] = FakeJWTProvider
    app.dependency_overrides[get_event_bus] = FakeEventBus

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_2fa_invalid_code")
def fixture_client_2fa_invalid_code():
    """Cliente con TOTP que rechaza el código."""
    user = _make_2fa_user()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(user=user)  # noqa: SIM901
    app.dependency_overrides[get_refresh_token_repository] = lambda: FakeRefreshTokenRepository()  # noqa: SIM901
    app.dependency_overrides[get_totp_provider] = lambda: FakeTOTPProvider(valid=False)  # noqa: SIM901
    app.dependency_overrides[get_jwt_provider] = FakeJWTProvider
    app.dependency_overrides[get_event_bus] = FakeEventBus

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLogin2FAEndpoint:
    """Tests para POST /api/v1/auth/login/2fa (T-40)."""

    def test_codigo_valido_devuelve_tokens(self, client_2fa_valid: TestClient):
        """TOTP correcto → 200 con access_token y refresh_token."""
        response = client_2fa_valid.post(
            "/api/v1/auth/login/2fa",
            json={"temp_token": _TEMP_TOKEN, "code": _VALID_CODE},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data.get("requires_2fa") is False

    def test_codigo_invalido_devuelve_401(self, client_2fa_invalid_code: TestClient):
        """TOTP incorrecto → 401."""
        response = client_2fa_invalid_code.post(
            "/api/v1/auth/login/2fa",
            json={"temp_token": _TEMP_TOKEN, "code": _INVALID_CODE},
        )
        assert response.status_code == 401

    def test_sin_body_devuelve_422(self, client_2fa_valid: TestClient):
        """Petición sin body → 422."""
        response = client_2fa_valid.post("/api/v1/auth/login/2fa")
        assert response.status_code == 422
