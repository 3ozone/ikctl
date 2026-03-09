"""Tests de integración — POST /api/v1/auth/password/reset (T-44).

T-44: POST /api/v1/auth/password/reset
    — Valida el token de reset y actualiza la contraseña del usuario.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.entities.verification_token import VerificationToken
from app.v1.auth.domain.value_objects.email import Email
from app.v1.auth.infrastructure.presentation.deps import (
    get_user_repository,
    get_verification_token_repository,
)
from main import app  # noqa: E402
from tests.v1.auth.test_presentation.conftest import (
    FakeUserRepository,
    FakeVerificationTokenRepository,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-reset-1"
_VALID_TOKEN_STR = "valid-reset-token-abc123"
_UNKNOWN_TOKEN_STR = "unknown-token-xyz"
_NEW_PASSWORD = "NewSecurePass123!"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=_USER_ID,
        name="Reset User",
        email=Email("reset@example.com"),
        password_hash="old-hashed-password",
        created_at=now,
        updated_at=now,
    )


def _make_reset_token(expired: bool = False) -> VerificationToken:
    now = datetime.now(timezone.utc)
    expires_at = now - \
        timedelta(hours=1) if expired else now + timedelta(hours=24)
    return VerificationToken(
        id="vt-reset-1",
        user_id=_USER_ID,
        token=_VALID_TOKEN_STR,
        token_type="password_reset",
        expires_at=expires_at,
        created_at=now,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="client_reset_valid")
def fixture_client_reset_valid():
    """Token válido y usuario existente — reset correcto."""
    user = _make_user()
    token = _make_reset_token()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user)
    app.dependency_overrides[get_verification_token_repository] = lambda: FakeVerificationTokenRepository(
        token=token)

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_reset_token_not_found")
def fixture_client_reset_token_not_found():
    """Token no existe en la base de datos."""
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
    )
    app.dependency_overrides[get_verification_token_repository] = lambda: FakeVerificationTokenRepository()

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_reset_token_expired")
def fixture_client_reset_token_expired():
    """Token expirado."""
    user = _make_user()
    token = _make_reset_token(expired=True)
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(user=user)  # noqa: SIM901
    app.dependency_overrides[get_verification_token_repository] = lambda: FakeVerificationTokenRepository(token=token)  # noqa: SIM901

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestResetPasswordEndpoint:
    """Tests para POST /api/v1/auth/password/reset (T-44)."""

    def test_reset_exitoso_devuelve_200(self, client_reset_valid: TestClient):
        """Token válido + nueva contraseña → 200 con mensaje de confirmación."""
        response = client_reset_valid.post(
            "/api/v1/auth/password/reset",
            json={"token": _VALID_TOKEN_STR, "new_password": _NEW_PASSWORD},
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_token_no_encontrado_devuelve_404(self, client_reset_token_not_found: TestClient):
        """Token desconocido → 404."""
        response = client_reset_token_not_found.post(
            "/api/v1/auth/password/reset",
            json={"token": _UNKNOWN_TOKEN_STR, "new_password": _NEW_PASSWORD},
        )
        assert response.status_code == 404

    def test_token_expirado_devuelve_400(self, client_reset_token_expired: TestClient):
        """Token expirado → 400."""
        response = client_reset_token_expired.post(
            "/api/v1/auth/password/reset",
            json={"token": _VALID_TOKEN_STR, "new_password": _NEW_PASSWORD},
        )
        assert response.status_code == 400

    def test_sin_body_devuelve_422(self, client_reset_valid: TestClient):
        """Body vacío → 422."""
        response = client_reset_valid.post("/api/v1/auth/password/reset")
        assert response.status_code == 422
