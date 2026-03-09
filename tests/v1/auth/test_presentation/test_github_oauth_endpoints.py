"""Tests de integración — GitHub OAuth (T-38, T-39).

T-38: POST /api/v1/auth/login/github        → devuelve URL de autorización GitHub
T-39: GET  /api/v1/auth/login/github/callback → intercambia code por tokens
"""
import asyncio
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.value_objects.email import Email
from app.v1.auth.infrastructure.presentation.deps import (
    get_event_bus,
    get_github_oauth,
    get_jwt_provider,
    get_refresh_token_repository,
    get_user_repository,
)
from main import app  # noqa: E402
from tests.v1.auth.test_presentation.conftest import (
    FakeEventBus,
    FakeRefreshTokenRepository,
    FakeUserRepository,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_FAKE_HASH = "fake-bcrypt-hash-only-for-tests"
_GITHUB_CODE = "github-auth-code-abc123"
_GITHUB_STATE = "random-csrf-state-xyz"
_GITHUB_EMAIL = "githubuser@example.com"
_GITHUB_NAME = "GitHub User"
_AUTH_URL = "https://github.com/login/oauth/authorize?client_id=test&state=xyz"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(email: str = _GITHUB_EMAIL) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id="user-gh-1",
        name=_GITHUB_NAME,
        email=Email(email),
        password_hash="OAUTH_NO_PASSWORD",
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Fakes específicos de GitHub OAuth
# ---------------------------------------------------------------------------

class FakeGitHubOAuth:
    """Fake en memoria para GitHubOAuth."""

    def __init__(
        self,
        user_info: dict[str, Any] | None = None,
        raise_on_exchange: Exception | None = None,
    ) -> None:
        self._user_info = user_info or {
            "email": _GITHUB_EMAIL,
            "name": _GITHUB_NAME,
            "id": "gh-12345",
        }
        self._raise_on_exchange = raise_on_exchange

    def get_authorization_url(self, state: str) -> str:  # noqa: ARG002
        return _AUTH_URL

    async def exchange_code_for_token(self, code: str) -> str:  # noqa: ARG002
        await asyncio.sleep(0)
        if self._raise_on_exchange:
            raise self._raise_on_exchange
        return "github-access-token-fake"

    async def get_user_info(self, access_token: str) -> dict[str, Any]:  # noqa: ARG002
        await asyncio.sleep(0)
        return self._user_info


class FakeJWTProvider:
    """Fake en memoria para JWTProvider."""

    def create_access_token(self, user_id: str, **_kwargs) -> object:
        """Fake — retorna token con valor predecible."""
        class _Token:
            token = f"fake-access-token-{user_id}"
        return _Token()

    def create_refresh_token(self, user_id: str, **_kwargs) -> object:
        """Fake — retorna refresh token con valor predecible."""
        class _Token:
            token = f"fake-refresh-token-{user_id}"
        return _Token()

    def decode_token(self, token: str) -> dict:  # noqa: ARG002
        """Fake — retorna payload fijo."""
        return {"sub": "user-gh-1"}

    def verify_token(self, token: str) -> bool:  # noqa: ARG002
        """Fake — siempre retorna True."""
        return True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="client_github_new_user")
def fixture_client_github_new_user():
    """Callback con code válido y usuario nuevo (no existe en DB)."""
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=None)
    app.dependency_overrides[get_refresh_token_repository] = lambda: FakeRefreshTokenRepository()  # noqa: SIM901
    app.dependency_overrides[get_github_oauth] = lambda: FakeGitHubOAuth()  # noqa: SIM901
    app.dependency_overrides[get_jwt_provider] = FakeJWTProvider
    app.dependency_overrides[get_event_bus] = FakeEventBus

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_github_existing_user")
def fixture_client_github_existing_user():
    """Callback con code válido y usuario ya registrado."""
    user = _make_user()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user)
    app.dependency_overrides[get_refresh_token_repository] = lambda: FakeRefreshTokenRepository()  # noqa: SIM901
    app.dependency_overrides[get_github_oauth] = lambda: FakeGitHubOAuth()  # noqa: SIM901
    app.dependency_overrides[get_jwt_provider] = FakeJWTProvider
    app.dependency_overrides[get_event_bus] = FakeEventBus

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_github_init")
def fixture_client_github_init():
    """Cliente para el endpoint de inicio OAuth (sin callback)."""
    app.dependency_overrides[get_github_oauth] = lambda: FakeGitHubOAuth()  # noqa: SIM901

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGitHubOAuthInitEndpoint:
    """Tests para POST /api/v1/auth/login/github (T-38)."""

    def test_devuelve_authorization_url(self, client_github_init: TestClient):
        """POST sin body → 200 con authorization_url de GitHub."""
        response = client_github_init.post("/api/v1/auth/login/github")
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "github.com" in data["authorization_url"]


class TestGitHubOAuthCallbackEndpoint:
    """Tests para GET /api/v1/auth/login/github/callback (T-39)."""

    def test_callback_usuario_nuevo_devuelve_tokens(self, client_github_new_user: TestClient):
        """Code válido + usuario nuevo → 200 con access_token y refresh_token."""
        response = client_github_new_user.get(
            "/api/v1/auth/login/github/callback",
            params={"code": _GITHUB_CODE, "state": _GITHUB_STATE},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_callback_usuario_existente_devuelve_tokens(self, client_github_existing_user: TestClient):
        """Code válido + usuario existente → 200 con tokens."""
        response = client_github_existing_user.get(
            "/api/v1/auth/login/github/callback",
            params={"code": _GITHUB_CODE, "state": _GITHUB_STATE},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_callback_sin_code_devuelve_422(self, client_github_new_user: TestClient):
        """Callback sin `code` → 422."""
        response = client_github_new_user.get(
            "/api/v1/auth/login/github/callback")
        assert response.status_code == 422
