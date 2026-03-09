"""Tests de integración — PUT /api/v1/auth/users/me/password (T-47).

T-47: PUT /api/v1/auth/users/me/password
    — Cambia la contraseña del usuario autenticado.
    — Valida la contraseña actual antes de cambiar.
    — Endpoint protegido: requiere Authorization: Bearer <token>.
"""
from datetime import datetime, timezone

import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.value_objects.email import Email
from app.v1.auth.infrastructure.presentation.deps import (
    get_password_history_repository,
    get_user_repository,
)
from main import app, jwt_provider  # noqa: E402
from tests.v1.auth.test_presentation.conftest import (
    FakePasswordHistoryRepository,
    FakeUserRepository,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-chpw-1"
_USER_EMAIL = "chpw@example.com"
_CURRENT_PASSWORD = "current-password"
_NEW_PASSWORD = "new-password-123"

# Hash real con cost=4 para que los tests sean rápidos
_CURRENT_PASSWORD_HASH = bcrypt.hashpw(
    _CURRENT_PASSWORD.encode("utf-8"),
    bcrypt.gensalt(rounds=4),
).decode("utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=_USER_ID,
        name="Change PW User",
        email=Email(_USER_EMAIL),
        password_hash=_CURRENT_PASSWORD_HASH,
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


@pytest.fixture(name="client_chpw_ok")
def fixture_client_chpw_ok():
    """Usuario autenticado con historial vacío."""
    user = _make_user()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(user=user)
    app.dependency_overrides[get_password_history_repository] = (
        lambda: FakePasswordHistoryRepository()
    )

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_chpw_not_found")
def fixture_client_chpw_not_found():
    """Usuario no existe en la DB."""
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository()
    app.dependency_overrides[get_password_history_repository] = (
        lambda: FakePasswordHistoryRepository()
    )

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_cambia_contrasena_correctamente(client_chpw_ok: TestClient):
    """PUT /users/me/password con credenciales válidas devuelve 200."""
    response = client_chpw_ok.put(
        "/api/v1/auth/users/me/password",
        json={
            "current_password": _CURRENT_PASSWORD,
            "new_password": _NEW_PASSWORD,
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert "message" in response.json()


def test_contrasena_actual_incorrecta_devuelve_400(client_chpw_ok: TestClient):
    """PUT /users/me/password con contraseña actual errónea devuelve 400."""
    response = client_chpw_ok.put(
        "/api/v1/auth/users/me/password",
        json={
            "current_password": "wrong-password",
            "new_password": _NEW_PASSWORD,
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 400


def test_usuario_no_encontrado_devuelve_404(client_chpw_not_found: TestClient):
    """PUT /users/me/password devuelve 404 si el usuario no existe."""
    response = client_chpw_not_found.put(
        "/api/v1/auth/users/me/password",
        json={
            "current_password": _CURRENT_PASSWORD,
            "new_password": _NEW_PASSWORD,
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 404


def test_sin_token_devuelve_401(client_chpw_ok: TestClient):
    """PUT /users/me/password sin token devuelve 401."""
    response = client_chpw_ok.put(
        "/api/v1/auth/users/me/password",
        json={
            "current_password": _CURRENT_PASSWORD,
            "new_password": _NEW_PASSWORD,
        },
    )

    assert response.status_code == 401
