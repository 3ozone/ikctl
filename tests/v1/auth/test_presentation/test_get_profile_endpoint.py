"""Tests de integración — GET /api/v1/auth/users/me (T-45).

T-45: GET /api/v1/auth/users/me
    — Devuelve el perfil del usuario autenticado.
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

_USER_ID = "user-me-1"
_USER_EMAIL = "me@example.com"
_USER_NAME = "Me User"


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

@pytest.fixture(name="client_me_ok")
def fixture_client_me_ok():
    """Usuario autenticado con perfil existente."""
    user = _make_user()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user)

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_me_not_found")
def fixture_client_me_not_found():
    """user_id válido pero usuario eliminado de la DB."""
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
    )

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetProfileEndpoint:
    """Tests para GET /api/v1/auth/users/me (T-45)."""

    def test_devuelve_perfil_del_usuario(self, client_me_ok: TestClient):
        """Token válido → 200 con datos del perfil."""
        response = client_me_ok.get(
            "/api/v1/auth/users/me",
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == _USER_ID
        assert data["email"] == _USER_EMAIL
        assert data["name"] == _USER_NAME

    def test_usuario_no_encontrado_devuelve_404(self, client_me_not_found: TestClient):
        """user_id válido pero usuario no existe en DB → 404."""
        response = client_me_not_found.get(
            "/api/v1/auth/users/me",
            headers=_auth_headers(),
        )
        assert response.status_code == 404

    def test_sin_token_devuelve_401(self, client_me_ok: TestClient):
        """Sin Authorization header → 401 del middleware."""
        response = client_me_ok.get("/api/v1/auth/users/me")
        assert response.status_code == 401
