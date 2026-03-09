"""Tests de integración — Middleware de response headers de seguridad (T-51.3).

T-51.3: SecurityHeadersMiddleware
    — Toda respuesta incluye:
        X-Content-Type-Options: nosniff
        X-Frame-Options: DENY
        Strict-Transport-Security: max-age=63072000; includeSubDomains
    — Aplica tanto a endpoints públicos como protegidos.
"""
import pytest
from fastapi.testclient import TestClient

from main import app  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="client")
def fixture_client():
    """Cliente sin overrides — prueba la app tal cual."""
    yield TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_respuesta_incluye_x_content_type_options(client: TestClient):
    """Toda respuesta incluye X-Content-Type-Options: nosniff."""
    response = client.get("/")

    assert response.headers.get("x-content-type-options") == "nosniff"


def test_respuesta_incluye_x_frame_options(client: TestClient):
    """Toda respuesta incluye X-Frame-Options: DENY."""
    response = client.get("/")

    assert response.headers.get("x-frame-options") == "DENY"


def test_respuesta_incluye_strict_transport_security(client: TestClient):
    """Toda respuesta incluye Strict-Transport-Security con max-age."""
    response = client.get("/")

    hsts = response.headers.get("strict-transport-security", "")
    assert "max-age=" in hsts
    assert "includeSubDomains" in hsts


def test_headers_presentes_en_endpoint_publico(client: TestClient):
    """Los headers de seguridad aparecen también en endpoints distintos de la raíz (/healthz)."""
    response = client.get("/healthz")

    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
