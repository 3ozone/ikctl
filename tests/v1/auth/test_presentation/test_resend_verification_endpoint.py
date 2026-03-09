"""Tests de integración — POST /api/v1/auth/resend-verification (T-36)."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.value_objects.email import Email
from app.v1.auth.infrastructure.presentation.deps import (
    get_email_service,
    get_event_bus,
    get_user_repository,
    get_verification_token_repository,
)
from main import app  # noqa: E402
from tests.v1.auth.test_presentation.conftest import (
    FakeEmailService,
    FakeEventBus,
    FakeUserRepository,
    FakeVerificationTokenRepository,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_FAKE_HASH = "fake-bcrypt-hash-only-for-tests"
_EXISTING_EMAIL = "existing@example.com"
_UNKNOWN_EMAIL = "unknown@example.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(email: str = _EXISTING_EMAIL) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id="user-1",
        name="Test User",
        email=Email(email),
        password_hash=_FAKE_HASH,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="client_user_exists")
def fixture_client_user_exists():
    """TestClient con usuario existente en el fake repo."""
    user = _make_user()

    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user)
    app.dependency_overrides[get_verification_token_repository] = lambda: FakeVerificationTokenRepository()
    app.dependency_overrides[get_email_service] = FakeEmailService
    app.dependency_overrides[get_event_bus] = FakeEventBus

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_user_not_found")
def fixture_client_user_not_found():
    """TestClient sin usuario en el fake repo (email no registrado)."""
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=None)
    app.dependency_overrides[get_verification_token_repository] = lambda: FakeVerificationTokenRepository()
    app.dependency_overrides[get_email_service] = FakeEmailService
    app.dependency_overrides[get_event_bus] = FakeEventBus

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestResendVerificationEndpoint:
    """Tests de integración para POST /api/v1/auth/resend-verification."""

    def test_email_existente_devuelve_200(self, client_user_exists: TestClient):
        """Usuario existe → 200 con mensaje de confirmación."""
        response = client_user_exists.post(
            "/api/v1/auth/resend-verification",
            json={"email": _EXISTING_EMAIL},
        )
        assert response.status_code == 200
        assert "message" in response.json()

    def test_email_no_registrado_devuelve_404(self, client_user_not_found: TestClient):
        """Email no existe en DB → 404."""
        response = client_user_not_found.post(
            "/api/v1/auth/resend-verification",
            json={"email": _UNKNOWN_EMAIL},
        )
        assert response.status_code == 404

    def test_sin_body_devuelve_422(self):
        """Body vacío → 422 (Pydantic validation error)."""
        with TestClient(app) as client:
            response = client.post("/api/v1/auth/resend-verification", json={})
        assert response.status_code == 422

    def test_email_invalido_devuelve_422(self):
        """Email con formato inválido → 422."""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/resend-verification",
                json={"email": "no-es-un-email"},
            )
        assert response.status_code == 422
