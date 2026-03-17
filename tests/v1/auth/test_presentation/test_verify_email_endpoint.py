"""Tests de integración — POST /api/v1/auth/verify-email (T-35)."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.verification_token import VerificationToken
from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.value_objects.email import Email
from app.v1.auth.infrastructure.presentation.deps import (
    get_event_bus,
    get_user_repository,
    get_verification_token_repository,
)
from main import app  # noqa: E402
from tests.v1.auth.test_presentation.conftest import (
    FakeEventBus,
    FakeUserRepository,
    FakeVerificationTokenRepository,
)


# ---------------------------------------------------------------------------
# Constantes — evitan que el linter detecte hard-coded secrets
# ---------------------------------------------------------------------------
_VALID_TOKEN_VAL = "test-verif-tok-valid-abc123"
_EXPIRED_TOKEN_VAL = "test-verif-tok-expired-xyz"
_UNKNOWN_TOKEN_VAL = "test-verif-tok-missing-000"
_FAKE_HASH = "fake-bcrypt-hash-only-for-tests"


# ---------------------------------------------------------------------------
# Helpers — entidades de prueba
# ---------------------------------------------------------------------------

def _make_valid_token(user_id: str = "user-1") -> VerificationToken:
    return VerificationToken(
        id="tok-1",
        user_id=user_id,
        token=_VALID_TOKEN_VAL,
        token_type="email_verification",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        created_at=datetime.now(timezone.utc),
    )


def _make_expired_token() -> VerificationToken:
    return VerificationToken(
        id="tok-2",
        user_id="user-2",
        token=_EXPIRED_TOKEN_VAL,
        token_type="email_verification",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        created_at=datetime.now(timezone.utc) - timedelta(hours=25),
    )


def _make_user(user_id: str = "user-1") -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        name="Test User",
        email=Email("test@example.com"),
        password_hash=_FAKE_HASH,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Fixtures — clientes con dependencias sustituidas
# ---------------------------------------------------------------------------

@pytest.fixture(name="client_valid")
def fixture_client_valid_token():
    """TestClient con un token válido en el fake repo."""
    token = _make_valid_token()
    user = _make_user(token.user_id)

    app.dependency_overrides[get_verification_token_repository] = (
        lambda: FakeVerificationTokenRepository(token=token)
    )
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user)
    app.dependency_overrides[get_event_bus] = FakeEventBus

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_expired")
def fixture_client_expired_token():
    """TestClient con un token expirado en el fake repo."""
    token = _make_expired_token()

    app.dependency_overrides[get_verification_token_repository] = (
        lambda: FakeVerificationTokenRepository(token=token)
    )
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
    )
    app.dependency_overrides[get_event_bus] = FakeEventBus

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(name="client_missing")
def fixture_client_missing_token():
    """TestClient sin token en el fake repo (token inexistente en DB)."""
    app.dependency_overrides[get_verification_token_repository] = (
        lambda: FakeVerificationTokenRepository(token=None)
    )
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
    )
    app.dependency_overrides[get_event_bus] = FakeEventBus

    yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestVerifyEmailEndpoint:
    """Tests de integración para POST /api/v1/auth/verify-email."""

    def test_token_valido_devuelve_200(self, client_valid: TestClient):
        """Token válido → 200 con mensaje de éxito."""
        response = client_valid.post(
            "/api/v1/auth/verify-email",
            json={"token": _VALID_TOKEN_VAL},
        )
        assert response.status_code == 200
        assert "message" in response.json()

    def test_token_no_encontrado_devuelve_404(self, client_missing: TestClient):
        """Token no existe en DB → 404."""
        response = client_missing.post(
            "/api/v1/auth/verify-email",
            json={"token": _UNKNOWN_TOKEN_VAL},
        )
        assert response.status_code == 404

    def test_token_expirado_devuelve_400(self, client_expired: TestClient):
        """Token expirado → 400 (InvalidVerificationTokenError)."""
        response = client_expired.post(
            "/api/v1/auth/verify-email",
            json={"token": _EXPIRED_TOKEN_VAL},
        )
        assert response.status_code == 400

    def test_sin_body_devuelve_422(self):
        """Body vacío → 422 (Pydantic validation error)."""
        with TestClient(app) as client:
            response = client.post("/api/v1/auth/verify-email", json={})
        assert response.status_code == 422
