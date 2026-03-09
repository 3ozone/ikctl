"""Tests de integración — POST /api/v1/auth/password/forgot (T-43).

T-43: POST /api/v1/auth/password/forgot
    — Genera un token de reset de contraseña y envía email.
    — Devuelve 200 siempre (no revela si el email existe, por seguridad).
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.value_objects.email import Email
from app.v1.auth.infrastructure.presentation.deps import (
    get_email_service,
    get_user_repository,
    get_verification_token_repository,
)
from main import app  # noqa: E402
from tests.v1.auth.test_presentation.conftest import (
    FakeEmailService,
    FakeUserRepository,
    FakeVerificationTokenRepository,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_EMAIL_REGISTERED = "user@example.com"
_EMAIL_UNKNOWN = "nobody@example.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(email: str = _EMAIL_REGISTERED) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id="user-forgot-1",
        name="Forgot User",
        email=Email(email),
        password_hash="hashed-password",
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="client_forgot_registered")
def fixture_client_forgot_registered():
    """Email registrado — genera token y envía email."""
    user = _make_user()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user)
    app.dependency_overrides[get_verification_token_repository] = lambda: FakeVerificationTokenRepository()
    app.dependency_overrides[get_email_service] = FakeEmailService

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_forgot_unknown")
def fixture_client_forgot_unknown():
    """Email no registrado — devuelve 200 igualmente (seguridad)."""
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
    )
    app.dependency_overrides[get_verification_token_repository] = lambda: FakeVerificationTokenRepository()
    app.dependency_overrides[get_email_service] = FakeEmailService

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestForgotPasswordEndpoint:
    """Tests para POST /api/v1/auth/password/forgot (T-43)."""

    def test_email_registrado_devuelve_200(self, client_forgot_registered: TestClient):
        """Email registrado → 200 con mensaje genérico."""
        response = client_forgot_registered.post(
            "/api/v1/auth/password/forgot",
            json={"email": _EMAIL_REGISTERED},
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_email_no_registrado_devuelve_200(self, client_forgot_unknown: TestClient):
        """Email desconocido → 200 igualmente (no revelar si existe)."""
        response = client_forgot_unknown.post(
            "/api/v1/auth/password/forgot",
            json={"email": _EMAIL_UNKNOWN},
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_sin_body_devuelve_422(self, client_forgot_registered: TestClient):
        """Body vacío → 422."""
        response = client_forgot_registered.post(
            "/api/v1/auth/password/forgot")
        assert response.status_code == 422
