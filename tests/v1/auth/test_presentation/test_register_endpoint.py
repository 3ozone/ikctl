"""Tests de integración — POST /api/v1/auth/register (T-34).

Verifica que el endpoint de registro:
  1. Devuelve 201 y llama a email_service.send_verification_email()
  2. Devuelve 409 cuando el email ya existe (sin enviar email)
"""
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
from main import app
from tests.v1.auth.test_presentation.conftest import (
    FakeEmailService,
    FakeEventBus,
    FakeUserRepository,
    FakeVerificationTokenRepository,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_HASH = "fake-bcrypt-hash-only-for-tests"
_EXISTING_EMAIL = "existing@example.com"


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

@pytest.fixture(name="client_empty_repo")
def fixture_client_empty_repo():
    """TestClient sin usuarios — registro debe funcionar."""
    fake_email_service = FakeEmailService()

    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=None)
    app.dependency_overrides[get_verification_token_repository] = lambda: FakeVerificationTokenRepository()
    app.dependency_overrides[get_email_service] = lambda: fake_email_service
    app.dependency_overrides[get_event_bus] = FakeEventBus

    yield TestClient(app), fake_email_service

    app.dependency_overrides.clear()


@pytest.fixture(name="client_email_exists")
def fixture_client_email_exists():
    """TestClient con usuario ya existente — registro debe devolver 409."""
    fake_email_service = FakeEmailService()
    existing_user = _make_user(_EXISTING_EMAIL)

    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=existing_user)
    app.dependency_overrides[get_verification_token_repository] = lambda: FakeVerificationTokenRepository()
    app.dependency_overrides[get_email_service] = lambda: fake_email_service
    app.dependency_overrides[get_event_bus] = FakeEventBus

    yield TestClient(app), fake_email_service

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_register_sends_verification_email(client_empty_repo):
    """Test 1: POST /register devuelve 201 y llama a send_verification_email."""
    client, email_service = client_empty_repo

    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "New User",
            "email": "newuser@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 201
    assert "user_id" in response.json()

    assert len(email_service.sent) == 1
    sent = email_service.sent[0]
    assert sent["type"] == "verification"
    assert sent["email"] == "newuser@example.com"
    assert sent["token"] != ""


def test_register_duplicate_email_returns_409_without_email(client_email_exists):
    """Test 2: POST /register con email duplicado devuelve 409 sin enviar email."""
    client, email_service = client_email_exists

    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Another User",
            "email": _EXISTING_EMAIL,
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 409
    assert len(email_service.sent) == 0
