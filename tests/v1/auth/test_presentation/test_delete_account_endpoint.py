"""Tests de integración — DELETE /api/v1/auth/users/me (T-51.4).

T-51.4: Endpoint DELETE /api/v1/auth/users/me — derecho al olvido GDPR
    — Usuario verificado y autenticado → 204 No Content.
    — Sin token de autenticación → 401.
    — Usuario con email no verificado → 403.
    — Usuario no encontrado en DB → 404.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.value_objects.email import Email
from app.v1.auth.infrastructure.presentation.deps import (
    get_user_repository,
    require_verified_email,
)
from main import app, jwt_provider  # noqa: E402
from tests.v1.auth.test_presentation.conftest import FakeUserRepository

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-delete-1"
_USER_EMAIL = "delete-me@example.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, verified: bool = True) -> User:
    """Crea un usuario de prueba."""
    now = datetime.now(timezone.utc)
    return User(
        id=_USER_ID,
        name="Delete Me",
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


@pytest.fixture(name="client_delete_verified")
def fixture_client_delete_verified():
    """Usuario autenticado con email verificado."""
    user = _make_user(verified=True)
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(user=user)

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_delete_unverified")
def fixture_client_delete_unverified():
    """Usuario autenticado con email NO verificado."""
    user = _make_user(verified=False)
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(user=user)

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_delete_not_found")
def fixture_client_delete_not_found():
    """Token válido pero usuario no existe en DB."""
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository()

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_no_auth")
def fixture_client_no_auth():
    """Cliente sin override — sin token en la request."""
    yield TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_delete_usuario_verificado_devuelve_204(client_delete_verified: TestClient):
    """DELETE /users/me con email verificado → 204 No Content."""
    response = client_delete_verified.delete(
        "/api/v1/auth/users/me",
        headers=_auth_headers(),
    )

    assert response.status_code == 204


def test_delete_sin_autenticacion_devuelve_401(client_no_auth: TestClient):
    """DELETE /users/me sin Bearer token → 401."""
    response = client_no_auth.delete("/api/v1/auth/users/me")

    assert response.status_code == 401


def test_delete_usuario_no_verificado_devuelve_403(client_delete_unverified: TestClient):
    """DELETE /users/me con email no verificado → 403."""
    response = client_delete_unverified.delete(
        "/api/v1/auth/users/me",
        headers=_auth_headers(),
    )

    assert response.status_code == 403


def test_delete_usuario_no_encontrado_devuelve_404(client_delete_not_found: TestClient):
    """DELETE /users/me cuando el usuario no existe en DB → 404."""
    response = client_delete_not_found.delete(
        "/api/v1/auth/users/me",
        headers=_auth_headers(),
    )

    assert response.status_code == 404
