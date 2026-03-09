"""Tests de integración — POST /api/v1/auth/users/me/2fa/enable (T-48).

T-48: POST /api/v1/auth/users/me/2fa/enable
    — Genera un secret TOTP y QR code para el usuario autenticado.
    — Devuelve TOTPSetupResponse con secret, qr_code_uri, etc.
    — Endpoint protegido: requiere Authorization: Bearer <token>.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.value_objects.email import Email
from app.v1.auth.infrastructure.presentation.deps import (
    get_totp_provider,
    get_user_repository,
)
from main import app, jwt_provider  # noqa: E402
from tests.v1.auth.test_presentation.conftest import (
    FakeTOTPProvider,
    FakeUserRepository,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-2fa-enable-1"
_USER_EMAIL = "enable2fa@example.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=_USER_ID,
        name="Enable 2FA User",
        email=Email(_USER_EMAIL),
        password_hash="hashed-password",
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )


def _auth_headers(user_id: str = _USER_ID) -> dict:
    token = jwt_provider.create_access_token(user_id=user_id).token
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="client_2fa_enable_ok")
def fixture_client_2fa_enable_ok():
    """Usuario autenticado con 2FA no habilitado."""
    user = _make_user()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(user=user)
    app.dependency_overrides[get_totp_provider] = lambda: FakeTOTPProvider()

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_2fa_enable_not_found")
def fixture_client_2fa_enable_not_found():
    """Usuario no existe en la DB."""
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository()
    app.dependency_overrides[get_totp_provider] = lambda: FakeTOTPProvider()

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_enable_2fa_devuelve_secret_y_qr(client_2fa_enable_ok: TestClient):
    """POST /users/me/2fa/enable devuelve 200 con secret y qr_code_uri."""
    response = client_2fa_enable_ok.post(
        "/api/v1/auth/users/me/2fa/enable",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert "secret" in data
    assert "qr_code_uri" in data
    assert data["secret"] == FakeTOTPProvider.FAKE_SECRET
    assert data["qr_code_uri"] == FakeTOTPProvider.FAKE_QR


def test_usuario_no_encontrado_devuelve_404(client_2fa_enable_not_found: TestClient):
    """POST /users/me/2fa/enable devuelve 404 si el usuario no existe."""
    response = client_2fa_enable_not_found.post(
        "/api/v1/auth/users/me/2fa/enable",
        headers=_auth_headers(),
    )

    assert response.status_code == 404


def test_sin_token_devuelve_401(client_2fa_enable_ok: TestClient):
    """POST /users/me/2fa/enable sin token devuelve 401."""
    response = client_2fa_enable_ok.post(
        "/api/v1/auth/users/me/2fa/enable",
    )

    assert response.status_code == 401
