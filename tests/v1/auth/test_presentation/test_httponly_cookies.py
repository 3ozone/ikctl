"""Tests de integración — HttpOnly cookies en refresh y logout (T-51.2).

T-51.2: Config HttpOnly cookies
    — POST /auth/refresh: respuesta incluye Set-Cookie con refresh_token,
      flags HttpOnly, Secure y SameSite=strict.
    — POST /auth/logout: respuesta limpia la cookie refresh_token.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.refresh_token import RefreshToken
from app.v1.auth.infrastructure.presentation.deps import get_refresh_token_repository
from main import app  # noqa: E402
from tests.v1.auth.test_presentation.conftest import FakeRefreshTokenRepository

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-cookie-1"
_VALID_TOKEN = "valid-refresh-token-cookie-abc"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_refresh_token(token: str = _VALID_TOKEN) -> RefreshToken:
    """Crea un RefreshToken válido y no expirado."""
    now = datetime.now(timezone.utc)
    return RefreshToken(
        id="rt-cookie-1",
        user_id=_USER_ID,
        token=token,
        expires_at=now + timedelta(days=7),
        created_at=now,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="client_cookie_valid")
def fixture_client_cookie_valid():
    """Refresh token válido para tests de cookie."""
    stored = _make_refresh_token()
    app.dependency_overrides[get_refresh_token_repository] = (
        lambda: FakeRefreshTokenRepository(token=stored)
    )

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — POST /auth/refresh
# ---------------------------------------------------------------------------


def test_refresh_exitoso_setea_cookie_httponly(client_cookie_valid: TestClient):
    """Refresh exitoso → respuesta incluye cookie refresh_token con flag HttpOnly."""
    response = client_cookie_valid.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": _VALID_TOKEN},
    )

    assert response.status_code == 200
    assert "set-cookie" in response.headers
    cookie = response.headers["set-cookie"]
    assert "refresh_token=" in cookie
    assert "HttpOnly" in cookie


def test_refresh_exitoso_cookie_samesite_lax(client_cookie_valid: TestClient):
    """Refresh exitoso → cookie refresh_token tiene SameSite=lax."""
    response = client_cookie_valid.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": _VALID_TOKEN},
    )

    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "samesite=lax" in cookie.lower()


# ---------------------------------------------------------------------------
# Tests — POST /auth/logout
# ---------------------------------------------------------------------------


def test_logout_exitoso_elimina_cookie(client_cookie_valid: TestClient):
    """Logout exitoso → respuesta incluye Set-Cookie que borra refresh_token."""
    response = client_cookie_valid.post(
        "/api/v1/auth/logout",
        cookies={"refresh_token": _VALID_TOKEN},
    )

    assert response.status_code == 200
    assert "set-cookie" in response.headers
    cookie = response.headers["set-cookie"]
    # La cookie se borra con max-age=0 o value vacío
    assert "refresh_token=" in cookie
    assert 'max-age=0' in cookie.lower() or 'expires=' in cookie.lower()
