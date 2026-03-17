"""Tests de integración — POST /api/v1/auth/logout (T-42).

T-42: POST /api/v1/auth/logout
    — Revoca el refresh token y lo elimina de la base de datos.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.refresh_token import RefreshToken
from app.v1.auth.infrastructure.presentation.deps import (
    get_refresh_token_repository,
)
from main import app  # noqa: E402
from tests.v1.auth.test_presentation.conftest import (
    FakeRefreshTokenRepository,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-logout-1"
_VALID_TOKEN = "valid-refresh-token-logout-abc"
_UNKNOWN_TOKEN = "unknown-token-xyz"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_refresh_token(token: str = _VALID_TOKEN) -> RefreshToken:
    now = datetime.now(timezone.utc)
    return RefreshToken(
        id="rt-logout-1",
        user_id=_USER_ID,
        token=token,
        expires_at=now + timedelta(days=7),
        created_at=now,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="client_logout_valid")
def fixture_client_logout_valid():
    """Refresh token válido — logout correcto."""
    stored = _make_refresh_token()
    app.dependency_overrides[get_refresh_token_repository] = lambda: FakeRefreshTokenRepository(
        token=stored)

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_logout_not_found")
def fixture_client_logout_not_found():
    """Refresh token desconocido — no existe en DB."""
    app.dependency_overrides[get_refresh_token_repository] = lambda: FakeRefreshTokenRepository(
    )

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLogoutEndpoint:
    """Tests para POST /api/v1/auth/logout (T-42)."""

    def test_logout_exitoso_devuelve_200(self, client_logout_valid: TestClient):
        """Refresh token válido → 200 con mensaje de confirmación."""
        response = client_logout_valid.post(
            "/api/v1/auth/logout",
            cookies={"refresh_token": _VALID_TOKEN},
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_token_no_encontrado_devuelve_401(self, client_logout_not_found: TestClient):
        """Refresh token desconocido → 401."""
        response = client_logout_not_found.post(
            "/api/v1/auth/logout",
            cookies={"refresh_token": _UNKNOWN_TOKEN},
        )
        assert response.status_code == 401

    def test_sin_cookie_devuelve_401(self, client_logout_valid: TestClient):
        """Sin cookie refresh_token → 401."""
        response = client_logout_valid.post("/api/v1/auth/logout")
        assert response.status_code == 401
