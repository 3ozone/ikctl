"""Tests de integración — GET /api/v1/auth/users/me/data (T-51.5).

T-51.5: Endpoint GET /api/v1/auth/users/me/data — exportación GDPR
    — Usuario verificado y autenticado → 200 con datos personales en JSON.
    — Sin token de autenticación → 401.
    — Usuario con email no verificado → 403.
    — Usuario no encontrado en DB → 404.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.value_objects.email import Email
from app.v1.auth.infrastructure.presentation.deps import get_user_repository
from main import app, jwt_provider  # noqa: E402
from tests.v1.auth.test_presentation.conftest import FakeUserRepository

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-export-1"
_USER_EMAIL = "export-me@example.com"
_USER_NAME = "Export User"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, verified: bool = True) -> User:
    """Crea un usuario de prueba."""
    now = datetime.now(timezone.utc)
    return User(
        id=_USER_ID,
        name=_USER_NAME,
        email=Email(_USER_EMAIL),
        password_hash="hashed-password",
        is_email_verified=verified,
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


@pytest.fixture(name="client_export_verified")
def fixture_client_export_verified():
    """Usuario autenticado con email verificado."""
    user = _make_user(verified=True)
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(user=user)

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_export_unverified")
def fixture_client_export_unverified():
    """Usuario autenticado con email NO verificado."""
    user = _make_user(verified=False)
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(user=user)

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_export_not_found")
def fixture_client_export_not_found():
    """Token válido pero usuario no existe en DB."""
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository()

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_no_auth")
def fixture_client_no_auth():
    """Cliente sin token de autenticación."""
    yield TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_export_usuario_verificado_devuelve_200_con_datos(client_export_verified: TestClient):
    """GET /users/me/data con email verificado → 200 con campos del usuario."""
    response = client_export_verified.get(
        "/api/v1/auth/users/me/data",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == _USER_ID
    assert data["email"] == _USER_EMAIL
    assert data["name"] == _USER_NAME
    assert "created_at" in data


def test_export_sin_autenticacion_devuelve_401(client_no_auth: TestClient):
    """GET /users/me/data sin Bearer token → 401."""
    response = client_no_auth.get("/api/v1/auth/users/me/data")

    assert response.status_code == 401


def test_export_usuario_no_verificado_devuelve_403(client_export_unverified: TestClient):
    """GET /users/me/data con email no verificado → 403."""
    response = client_export_unverified.get(
        "/api/v1/auth/users/me/data",
        headers=_auth_headers(),
    )

    assert response.status_code == 403


def test_export_usuario_no_encontrado_devuelve_404(client_export_not_found: TestClient):
    """GET /users/me/data cuando el usuario no existe en DB → 404."""
    response = client_export_not_found.get(
        "/api/v1/auth/users/me/data",
        headers=_auth_headers(),
    )

    assert response.status_code == 404
