"""Tests de integración — Dependencia require_verified_email (T-51.1).

T-51.1: Dependencia require_verified_email (RN-02)
    — Solo usuarios con email verificado pueden acceder a endpoints críticos.
    — Si el email no está verificado → 403.
    — Si el usuario no existe → 404.

Se prueba a través de GET /api/v1/auth/users/me como endpoint representativo.
Los mismos tests aplican a cualquier endpoint que use Depends(require_verified_email).
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

_USER_ID = "user-verified-1"
_USER_EMAIL = "verified@example.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, verified: bool) -> User:
    """Crea un usuario con email verificado o no según el parámetro."""
    now = datetime.now(timezone.utc)
    return User(
        id=_USER_ID,
        name="Test User",
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


@pytest.fixture(name="client_verified")
def fixture_client_verified():
    """Usuario autenticado con email verificado."""
    user = _make_user(verified=True)
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user)

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_unverified")
def fixture_client_unverified():
    """Usuario autenticado pero con email NO verificado."""
    user = _make_user(verified=False)
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user)

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_user_not_found")
def fixture_client_user_not_found():
    """Token válido pero el usuario no existe en la DB."""
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
    )

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_usuario_verificado_accede_correctamente(client_verified: TestClient):
    """GET /users/me con email verificado devuelve 200."""
    response = client_verified.get(
        "/api/v1/auth/users/me",
        headers=_auth_headers(),
    )

    assert response.status_code == 200


def test_usuario_no_verificado_devuelve_403(client_unverified: TestClient):
    """GET /users/me con email no verificado devuelve 403."""
    response = client_unverified.get(
        "/api/v1/auth/users/me",
        headers=_auth_headers(),
    )

    assert response.status_code == 403


def test_usuario_no_encontrado_devuelve_404(client_user_not_found: TestClient):
    """GET /users/me cuando el usuario no existe en DB devuelve 404."""
    response = client_user_not_found.get(
        "/api/v1/auth/users/me",
        headers=_auth_headers(),
    )

    assert response.status_code == 404
