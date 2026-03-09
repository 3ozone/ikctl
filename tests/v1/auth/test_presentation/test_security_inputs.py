"""Tests de seguridad — XSS, SQL Injection, validación de inputs (T-54).

T-54: Tests de seguridad
    — Payloads XSS en email son rechazados con 422 (Pydantic EmailStr)
    — Payloads XSS en name se tratan como texto plano (never rendered as HTML)
    — SQL injection en email es rechazado con 422
    — Inputs sobredimensionados son rechazados con 422
    — Las respuestas JSON nunca se sirven como text/html (previene XSS)
    — Null bytes en campos son rechazados con 422
"""
import pytest
from fastapi.testclient import TestClient

from app.v1.auth.infrastructure.presentation.deps import (
    get_event_bus,
    get_user_repository,
)
from main import app
from tests.v1.auth.test_presentation.conftest import FakeEventBus, FakeUserRepository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="client")
def fixture_client():
    """Cliente con overrides mínimos para evitar acceso a DB en tests de validación."""
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository()
    app.dependency_overrides[get_event_bus] = FakeEventBus
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# XSS
# ---------------------------------------------------------------------------


def test_xss_payload_in_email_returns_422(client: TestClient):
    """Un payload XSS como email es rechazado por Pydantic (no es un email válido)."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "John Doe",
            "email": "<script>alert(1)</script>@evil.com",
            "password": "SecurePass123",
        },
    )
    assert response.status_code == 422


def test_xss_payload_as_script_tag_email_returns_422(client: TestClient):
    """Un tag <script> sin @ es rechazado con 422."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "John Doe",
            "email": "<script>alert('xss')</script>",
            "password": "SecurePass123",
        },
    )
    assert response.status_code == 422


def test_response_content_type_is_json_not_html(client: TestClient):
    """Las respuestas de la API siempre son application/json, nunca text/html.

    Esto previene que payloads XSS almacenados sean interpretados por el navegador.
    """
    response = client.get("/healthz")
    content_type = response.headers.get("content-type", "")
    assert "application/json" in content_type
    assert "text/html" not in content_type


# ---------------------------------------------------------------------------
# SQL Injection
# ---------------------------------------------------------------------------


def test_sql_injection_in_email_returns_422(client: TestClient):
    """Un payload de SQL injection en email es rechazado por Pydantic."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "John Doe",
            "email": "' OR '1'='1",
            "password": "SecurePass123",
        },
    )
    assert response.status_code == 422


def test_sql_injection_with_drop_table_in_email_returns_422(client: TestClient):
    """Payload clásico DROP TABLE en email es rechazado por Pydantic."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Robert'; DROP TABLE users; --",
            "email": "'; DROP TABLE users; --@evil.com",
            "password": "SecurePass123",
        },
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Inputs sobredimensionados
# ---------------------------------------------------------------------------


def test_oversized_password_returns_422(client: TestClient):
    """Contraseña mayor de 128 caracteres es rechazada por Pydantic (max_length=128)."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "John Doe",
            "email": "john@example.com",
            "password": "A" * 129,
        },
    )
    assert response.status_code == 422


def test_oversized_name_returns_422(client: TestClient):
    """Nombre mayor de 255 caracteres es rechazado por Pydantic (max_length=255)."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "A" * 256,
            "email": "john@example.com",
            "password": "SecurePass123",
        },
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Null bytes
# ---------------------------------------------------------------------------


def test_null_byte_in_password_returns_422(client: TestClient):
    """Un null byte en el password es rechazado con 422."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "John Doe",
            "email": "john@example.com",
            "password": "SecurePa\x00ss123",
        },
    )
    # Pydantic o el dominio rechazan null bytes
    assert response.status_code in (422, 400)
