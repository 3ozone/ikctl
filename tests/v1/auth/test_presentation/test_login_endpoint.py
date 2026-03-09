"""Tests de integración — POST /api/v1/auth/login (T-37)."""
from datetime import datetime, timezone

import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.value_objects.email import Email
from app.v1.auth.infrastructure.presentation.deps import (
    get_event_bus,
    get_jwt_provider,
    get_login_attempt_tracker,
    get_refresh_token_repository,
    get_user_repository,
)
from main import app  # noqa: E402
from tests.v1.auth.test_presentation.conftest import (
    FakeEventBus,
    FakeJWTProvider,
    FakeLoginAttemptTracker,
    FakeRefreshTokenRepository,
    FakeUserRepository,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_PASSWORD = "TestPass123!"
# Hash bcrypt con rounds=4 (rápido para tests, compatible con VerifyPassword)
_PASSWORD_HASH = bcrypt.hashpw(
    _PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
_WRONG_PASSWORD = "WrongPass999!"
_EXISTING_EMAIL = "user@example.com"
_UNKNOWN_EMAIL = "nobody@example.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(
    email: str = _EXISTING_EMAIL,
    password_hash: str = _PASSWORD_HASH,
    is_2fa_enabled: bool = False,
) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id="user-1",
        name="Test User",
        email=Email(email),
        password_hash=password_hash,
        created_at=now,
        updated_at=now,
        is_2fa_enabled=is_2fa_enabled,
        totp_secret="TOTP_SECRET_BASE32" if is_2fa_enabled else None,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _override_deps(
    user: User | None = None,
    blocked: bool = False,
) -> tuple:
    """Registra overrides en app y retorna los fakes para inspección."""
    fake_refresh_repo = FakeRefreshTokenRepository()
    fake_tracker = FakeLoginAttemptTracker(blocked=blocked)

    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(user=user)  # noqa: SIM901
    app.dependency_overrides[get_refresh_token_repository] = lambda: fake_refresh_repo  # noqa: SIM901
    app.dependency_overrides[get_login_attempt_tracker] = lambda: fake_tracker  # noqa: SIM901
    app.dependency_overrides[get_jwt_provider] = FakeJWTProvider
    app.dependency_overrides[get_event_bus] = FakeEventBus

    return fake_refresh_repo, fake_tracker


@pytest.fixture(name="client_login_ok")
def fixture_client_login_ok():
    """Usuario existente, contraseña correcta, sin 2FA."""
    _override_deps(user=_make_user())
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(name="client_user_not_found")
def fixture_client_user_not_found():
    """Email no registrado."""
    _override_deps(user=None)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(name="client_blocked")
def fixture_client_blocked():
    """Usuario bloqueado por intentos fallidos."""
    _override_deps(user=_make_user(), blocked=True)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(name="client_2fa_required")
def fixture_client_2fa_required():
    """Usuario con 2FA activado."""
    _override_deps(user=_make_user(is_2fa_enabled=True))
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLoginEndpoint:
    """Tests de integración para POST /api/v1/auth/login."""

    def test_login_exitoso_devuelve_tokens(self, client_login_ok: TestClient):
        """Credenciales correctas sin 2FA → 200 con access_token y refresh_token."""
        response = client_login_ok.post(
            "/api/v1/auth/login",
            json={"email": _EXISTING_EMAIL, "password": _PASSWORD},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data.get("token_type") == "Bearer"

    def test_email_no_registrado_devuelve_401(self, client_user_not_found: TestClient):
        """Email desconocido → 401 (no se revela si el email existe)."""
        response = client_user_not_found.post(
            "/api/v1/auth/login",
            json={"email": _UNKNOWN_EMAIL, "password": _PASSWORD},
        )
        assert response.status_code == 401

    def test_contrasena_incorrecta_devuelve_401(self, client_login_ok: TestClient):
        """Contraseña incorrecta → 401."""
        response = client_login_ok.post(
            "/api/v1/auth/login",
            json={"email": _EXISTING_EMAIL, "password": _WRONG_PASSWORD},
        )
        assert response.status_code == 401

    def test_usuario_bloqueado_devuelve_429(self, client_blocked: TestClient):
        """Usuario bloqueado por intentos fallidos → 429."""
        response = client_blocked.post(
            "/api/v1/auth/login",
            json={"email": _EXISTING_EMAIL, "password": _PASSWORD},
        )
        assert response.status_code == 429

    def test_usuario_con_2fa_devuelve_requires_2fa(self, client_2fa_required: TestClient):
        """Usuario con 2FA activado → 200 con requires_2fa=true y temp_token."""
        response = client_2fa_required.post(
            "/api/v1/auth/login",
            json={"email": _EXISTING_EMAIL, "password": _PASSWORD},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("requires_2fa") is True
        assert data.get("temp_token") is not None

    def test_sin_body_devuelve_422(self):
        """Body vacío → 422."""
        with TestClient(app) as client:
            response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422
