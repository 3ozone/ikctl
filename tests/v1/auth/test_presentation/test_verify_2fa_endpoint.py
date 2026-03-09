"""Tests de integración — POST /api/v1/auth/users/me/2fa/verify (T-49).

T-49: POST /api/v1/auth/users/me/2fa/verify
    — Verifica un código TOTP de 6 dígitos para confirmar el setup 2FA.
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

_USER_ID = "user-2fa-verify-1"
_USER_EMAIL = "verify2fa@example.com"
_TOTP_SECRET = FakeTOTPProvider.FAKE_SECRET


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user_with_2fa() -> User:
    """Usuario con 2FA habilitado y secret configurado."""
    now = datetime.now(timezone.utc)
    user = User(
        id=_USER_ID,
        name="Verify 2FA User",
        email=Email(_USER_EMAIL),
        password_hash="hashed-password",
        totp_secret=_TOTP_SECRET,
        is_2fa_enabled=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    return user


def _make_user_without_2fa() -> User:
    """Usuario sin 2FA habilitado."""
    now = datetime.now(timezone.utc)
    return User(
        id=_USER_ID,
        name="No 2FA User",
        email=Email(_USER_EMAIL),
        password_hash="hashed-password",
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )


def _auth_headers(user_id: str = _USER_ID) -> dict:
    """Genera headers con Bearer token real."""
    token = jwt_provider.create_access_token(user_id=user_id).token
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="client_verify_ok")
def fixture_client_verify_ok():
    """Usuario con 2FA habilitado."""
    user = _make_user_with_2fa()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(user=user)
    app.dependency_overrides[get_totp_provider] = lambda: FakeTOTPProvider()

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_verify_no_2fa")
def fixture_client_verify_no_2fa():
    """Usuario sin 2FA habilitado."""
    user = _make_user_without_2fa()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(user=user)
    app.dependency_overrides[get_totp_provider] = lambda: FakeTOTPProvider()

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_verify_not_found")
def fixture_client_verify_not_found():
    """Usuario no existe."""
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository()
    app.dependency_overrides[get_totp_provider] = lambda: FakeTOTPProvider()

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_codigo_valido_devuelve_200(client_verify_ok: TestClient):
    """POST /users/me/2fa/verify con código correcto devuelve 200."""
    response = client_verify_ok.post(
        "/api/v1/auth/users/me/2fa/verify",
        json={"code": "123456"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert "message" in response.json()


def test_codigo_invalido_devuelve_400(client_verify_ok: TestClient):
    """POST /users/me/2fa/verify con código incorrecto devuelve 400."""
    response = client_verify_ok.post(
        "/api/v1/auth/users/me/2fa/verify",
        json={"code": "000000"},
        headers=_auth_headers(),
    )

    assert response.status_code == 400


def test_usuario_sin_2fa_devuelve_403(client_verify_no_2fa: TestClient):
    """POST /users/me/2fa/verify sin 2FA habilitado devuelve 403."""
    response = client_verify_no_2fa.post(
        "/api/v1/auth/users/me/2fa/verify",
        json={"code": "123456"},
        headers=_auth_headers(),
    )

    assert response.status_code == 403


def test_usuario_no_encontrado_devuelve_404(client_verify_not_found: TestClient):
    """POST /users/me/2fa/verify sin usuario devuelve 404."""
    response = client_verify_not_found.post(
        "/api/v1/auth/users/me/2fa/verify",
        json={"code": "123456"},
        headers=_auth_headers(),
    )

    assert response.status_code == 404


def test_sin_token_devuelve_401(client_verify_ok: TestClient):
    """POST /users/me/2fa/verify sin token devuelve 401."""
    response = client_verify_ok.post(
        "/api/v1/auth/users/me/2fa/verify",
        json={"code": "123456"},
    )

    assert response.status_code == 401
