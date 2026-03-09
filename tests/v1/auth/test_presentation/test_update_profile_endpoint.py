"""Tests de integración — PUT /api/v1/auth/users/me (T-46).

T-46: PUT /api/v1/auth/users/me
    — Actualiza el nombre del usuario autenticado.
    — Devuelve el perfil actualizado (UserProfileResponse).
    — Endpoint protegido: requiere Authorization: Bearer <token>.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.value_objects.email import Email
from app.v1.auth.infrastructure.presentation.deps import (
    get_user_repository,
)
from main import app, jwt_provider  # noqa: E402
from tests.v1.auth.test_presentation.conftest import (
    FakeUserRepository,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-update-1"
_USER_EMAIL = "update@example.com"
_USER_NAME = "Original Name"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=_USER_ID,
        name=_USER_NAME,
        email=Email(_USER_EMAIL),
        password_hash="hashed-password",
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )


def _auth_headers(user_id: str = _USER_ID) -> dict:
    """Genera headers con Bearer token real usando el jwt_provider de la app."""
    token = jwt_provider.create_access_token(user_id=user_id).token
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="client_update_ok")
def fixture_client_update_ok():
    """Usuario autenticado con perfil existente."""
    user = _make_user()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user
    )

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_update_not_found")
def fixture_client_update_not_found():
    """user_id válido pero usuario no existe en la DB."""
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
    )

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_actualiza_nombre_correctamente(client_update_ok: TestClient):
    """PUT /users/me actualiza el nombre y devuelve perfil actualizado."""
    response = client_update_ok.put(
        "/api/v1/auth/users/me",
        json={"name": "Nuevo Nombre"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Nuevo Nombre"
    assert data["email"] == _USER_EMAIL
    assert data["id"] == _USER_ID


def test_usuario_no_encontrado_devuelve_404(client_update_not_found: TestClient):
    """PUT /users/me devuelve 404 si el usuario no existe."""
    response = client_update_not_found.put(
        "/api/v1/auth/users/me",
        json={"name": "Nuevo Nombre"},
        headers=_auth_headers(),
    )

    assert response.status_code == 404


def test_sin_token_devuelve_401(client_update_ok: TestClient):
    """PUT /users/me devuelve 401 si no se envía token."""
    response = client_update_ok.put(
        "/api/v1/auth/users/me",
        json={"name": "Nuevo Nombre"},
    )

    assert response.status_code == 401


def test_nombre_vacio_devuelve_422(client_update_ok: TestClient):
    """PUT /users/me devuelve 422 si el nombre está vacío."""
    response = client_update_ok.put(
        "/api/v1/auth/users/me",
        json={"name": ""},
        headers=_auth_headers(),
    )

    assert response.status_code == 422
