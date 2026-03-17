"""Tests de integración — Logging estructurado de eventos críticos (T-51.6).

T-51.6: Logging estructurado en endpoints críticos.
    — Login exitoso → logger.info("login_success", user_id=..., email=...)
    — Login fallido → logger.warning("login_failed", email=...)
    — Password changed → logger.info("password_changed", user_id=...)
    — 2FA enabled → logger.info("2fa_enabled", user_id=...)
    — Token refreshed → logger.info("token_refreshed", user_id=...)

Estrategia: se parchea `routes.logger` con un MagicMock para capturar
las llamadas sin depender de caplog ni de la configuración de structlog.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.refresh_token import RefreshToken
from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.value_objects.email import Email
from app.v1.auth.infrastructure.presentation.deps import (
    get_event_bus,
    get_jwt_provider,
    get_login_attempt_tracker,
    get_password_history_repository,
    get_refresh_token_repository,
    get_totp_provider,
    get_user_repository,
)
from main import app, jwt_provider  # noqa: E402
from tests.v1.auth.test_presentation.conftest import (
    FakeEventBus,
    FakeJWTProvider,
    FakeLoginAttemptTracker,
    FakePasswordHistoryRepository,
    FakeRefreshTokenRepository,
    FakeTOTPProvider,
    FakeUserRepository,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-log-1"
_USER_EMAIL = "log-user@example.com"
_VALID_REFRESH_TOKEN = "valid-refresh-token-log"
_CURRENT_PASSWORD = "password"
# Hash bcrypt con rounds=4 (rápido para tests)
_HASHED_PASSWORD = bcrypt.hashpw(
    _CURRENT_PASSWORD.encode("utf-8"), bcrypt.gensalt(rounds=4)
).decode("utf-8")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, verified: bool = True, totp_secret: str | None = None) -> User:
    """Crea un usuario de prueba."""
    now = datetime.now(timezone.utc)
    return User(
        id=_USER_ID,
        name="Log User",
        email=Email(_USER_EMAIL),
        password_hash=_HASHED_PASSWORD,
        is_email_verified=verified,
        totp_secret=totp_secret,
        is_2fa_enabled=totp_secret is not None,
        created_at=now,
        updated_at=now,
    )


def _make_refresh_token() -> RefreshToken:
    """Crea un RefreshToken válido."""
    now = datetime.now(timezone.utc)
    return RefreshToken(
        id="rt-log-1",
        user_id=_USER_ID,
        token=_VALID_REFRESH_TOKEN,
        expires_at=now + timedelta(days=7),
        created_at=now,
    )


def _auth_headers() -> dict:
    """Genera headers con Bearer token real."""
    token = jwt_provider.create_access_token(user_id=_USER_ID).token
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests — Login
# ---------------------------------------------------------------------------


def test_login_exitoso_emite_log_login_success():
    """Login exitoso → logger.info llamado con evento 'login_success' y user_id."""
    user = _make_user()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user)
    app.dependency_overrides[get_refresh_token_repository] = lambda: FakeRefreshTokenRepository(
    )
    app.dependency_overrides[get_login_attempt_tracker] = lambda: FakeLoginAttemptTracker(
    )
    app.dependency_overrides[get_jwt_provider] = FakeJWTProvider
    app.dependency_overrides[get_event_bus] = lambda: FakeEventBus()

    try:
        with patch("app.v1.auth.infrastructure.presentation.routes.logger") as mock_logger:
            client = TestClient(app)
            response = client.post(
                "/api/v1/auth/login",
                json={"email": _USER_EMAIL, "password": _CURRENT_PASSWORD},
            )

        assert response.status_code == 200
        mock_logger.info.assert_called_once()
        call_kwargs = mock_logger.info.call_args
        assert call_kwargs.args[0] == "login_success"
        assert call_kwargs.kwargs.get("user_id") == _USER_ID
    finally:
        app.dependency_overrides.clear()


def test_login_fallido_emite_log_login_failed():
    """Login con contraseña incorrecta → logger.warning llamado con 'login_failed' y email."""
    user = _make_user()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user)
    app.dependency_overrides[get_refresh_token_repository] = lambda: FakeRefreshTokenRepository(
    )
    app.dependency_overrides[get_login_attempt_tracker] = lambda: FakeLoginAttemptTracker(
    )
    app.dependency_overrides[get_jwt_provider] = FakeJWTProvider
    app.dependency_overrides[get_event_bus] = lambda: FakeEventBus()

    try:
        with patch("app.v1.auth.infrastructure.presentation.routes.logger") as mock_logger:
            client = TestClient(app)
            response = client.post(
                "/api/v1/auth/login",
                json={"email": _USER_EMAIL, "password": "wrong-password"},
            )

        assert response.status_code == 401
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args
        assert call_kwargs.args[0] == "login_failed"
        assert call_kwargs.kwargs.get("email") == _USER_EMAIL
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — Password change
# ---------------------------------------------------------------------------


def test_password_change_emite_log_password_changed():
    """Cambio de contraseña exitoso → logger.info con 'password_changed' y user_id."""
    user = _make_user()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user)
    app.dependency_overrides[get_password_history_repository] = (
        lambda: FakePasswordHistoryRepository()
    )

    try:
        with patch("app.v1.auth.infrastructure.presentation.routes.logger") as mock_logger:
            client = TestClient(app)
            response = client.put(
                "/api/v1/auth/users/me/password",
                headers=_auth_headers(),
                json={
                    "current_password": "password",
                    "new_password": "NewPassword123!",
                    "confirm_password": "NewPassword123!",
                },
            )

        assert response.status_code == 200
        calls = [c.args[0] for c in mock_logger.info.call_args_list]
        assert "password_changed" in calls
        matching = next(
            c for c in mock_logger.info.call_args_list if c.args[0] == "password_changed")
        assert matching.kwargs.get("user_id") == _USER_ID
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — 2FA enable
# ---------------------------------------------------------------------------


def test_enable_2fa_emite_log_2fa_enabled():
    """Habilitar 2FA → logger.info con '2fa_enabled' y user_id."""
    user = _make_user()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user)
    app.dependency_overrides[get_totp_provider] = lambda: FakeTOTPProvider()

    try:
        with patch("app.v1.auth.infrastructure.presentation.routes.logger") as mock_logger:
            client = TestClient(app)
            response = client.post(
                "/api/v1/auth/users/me/2fa/enable",
                headers=_auth_headers(),
            )

        assert response.status_code == 200
        calls = [c.args[0] for c in mock_logger.info.call_args_list]
        assert "2fa_enabled" in calls
        matching = next(
            c for c in mock_logger.info.call_args_list if c.args[0] == "2fa_enabled")
        assert matching.kwargs.get("user_id") == _USER_ID
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — Token refresh
# ---------------------------------------------------------------------------


def test_token_refresh_emite_log_token_refreshed():
    """Refresh de token exitoso → logger.info con 'token_refreshed'."""
    stored = _make_refresh_token()
    app.dependency_overrides[get_refresh_token_repository] = (
        lambda: FakeRefreshTokenRepository(token=stored)
    )

    try:
        with patch("app.v1.auth.infrastructure.presentation.routes.logger") as mock_logger:
            client = TestClient(app)
            response = client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": _VALID_REFRESH_TOKEN},
            )

        assert response.status_code == 200
        mock_logger.info.assert_called_once()
        call_kwargs = mock_logger.info.call_args
        assert call_kwargs.args[0] == "token_refreshed"
    finally:
        app.dependency_overrides.clear()
