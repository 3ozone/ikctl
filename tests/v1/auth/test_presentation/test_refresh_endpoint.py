"""Tests de integración — POST /api/v1/auth/refresh (T-41).

T-41: POST /api/v1/auth/refresh
    — Renueva el access token usando un refresh token válido.
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

_USER_ID = "user-refresh-1"
_VALID_TOKEN = "valid-refresh-token-abc123"
_UNKNOWN_TOKEN = "unknown-token-xyz"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_refresh_token(
    token: str = _VALID_TOKEN,
    expired: bool = False,
) -> RefreshToken:
    now = datetime.now(timezone.utc)
    expires_at = now - \
        timedelta(days=1) if expired else now + timedelta(days=7)
    return RefreshToken(
        id="rt-1",
        user_id=_USER_ID,
        token=token,
        expires_at=expires_at,
        created_at=now,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="client_refresh_valid")
def fixture_client_refresh_valid():
    """Refresh token válido y no expirado."""
    stored = _make_refresh_token()
    app.dependency_overrides[get_refresh_token_repository] = lambda: FakeRefreshTokenRepository(
        token=stored)

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_refresh_expired")
def fixture_client_refresh_expired():
    """Refresh token expirado."""
    stored = _make_refresh_token(expired=True)
    app.dependency_overrides[get_refresh_token_repository] = lambda: FakeRefreshTokenRepository(
        token=stored)

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_refresh_not_found")
def fixture_client_refresh_not_found():
    """Refresh token no existe en la base de datos."""
    app.dependency_overrides[get_refresh_token_repository] = lambda: FakeRefreshTokenRepository()  # noqa: SIM901

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRefreshEndpoint:
    """Tests para POST /api/v1/auth/refresh (T-41)."""

    def test_token_valido_devuelve_nuevo_access_token(self, client_refresh_valid: TestClient):
        """Refresh token válido → 200 con nuevo access_token."""
        response = client_refresh_valid.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": _VALID_TOKEN},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_token_no_encontrado_devuelve_401(self, client_refresh_not_found: TestClient):
        """Refresh token desconocido → 401."""
        response = client_refresh_not_found.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": _UNKNOWN_TOKEN},
        )
        assert response.status_code == 401

    def test_token_expirado_devuelve_401(self, client_refresh_expired: TestClient):
        """Refresh token expirado → 401."""
        response = client_refresh_expired.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": _VALID_TOKEN},
        )
        assert response.status_code == 401

    def test_sin_cookie_devuelve_401(self, client_refresh_valid: TestClient):
        """Sin cookie refresh_token → 401."""
        response = client_refresh_valid.post("/api/v1/auth/refresh")
        assert response.status_code == 401
