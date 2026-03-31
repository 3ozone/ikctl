"""Tests para RateLimitMiddleware — T-44.1.

Cubre:
- Health check: máx 10 req/min por (user_id, server_id)
- Ad-hoc command: máx 30 req/hora por user_id
- Devuelve 429 con header Retry-After al superar el límite
- Rutas no sujetas a rate limit pasan libremente
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.v1.servers.infrastructure.presentation.rate_limit_middleware import RateLimitMiddleware


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    """Crea una app mínima con el middleware y rutas de prueba."""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/v1/servers/{server_id}/health")
    async def health(server_id: str) -> dict:
        return {"status": "ok"}

    @app.post("/api/v1/servers/{server_id}/exec")
    async def exec_cmd(server_id: str) -> dict:
        return {"output": "ok"}

    @app.get("/api/v1/servers")
    async def list_servers() -> dict:
        return {"servers": []}

    return app


@pytest.fixture()
def client() -> TestClient:
    """Fixture TestClient con la app que incluye el RateLimitMiddleware."""
    return TestClient(_make_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# T-44.1-1: Health check — superar límite devuelve 429 con Retry-After
# ---------------------------------------------------------------------------


def test_health_check_rate_limit_returns_429_after_limit(client: TestClient) -> None:
    """Superar 10 req/min en health check devuelve 429 con Retry-After."""
    headers = {"X-User-Id": "user-1"}
    # Las primeras 10 deben pasar
    for _ in range(10):
        resp = client.get("/api/v1/servers/srv-1/health", headers=headers)
        assert resp.status_code == 200

    # La 11ª debe ser rechazada
    resp = client.get("/api/v1/servers/srv-1/health", headers=headers)
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


# ---------------------------------------------------------------------------
# T-44.1-2: Health check — límite es por (user_id, server_id)
# ---------------------------------------------------------------------------


def test_health_check_rate_limit_is_per_user_and_server(client: TestClient) -> None:
    """El límite de health check es independiente por usuario y servidor."""
    # Agotar límite para user-2 en srv-A
    headers_u2_srvA = {"X-User-Id": "user-2"}
    for _ in range(10):
        client.get("/api/v1/servers/srv-A/health", headers=headers_u2_srvA)

    # user-2 en srv-A bloqueado
    assert client.get("/api/v1/servers/srv-A/health",
                      headers=headers_u2_srvA).status_code == 429

    # user-2 en srv-B NO bloqueado
    assert client.get("/api/v1/servers/srv-B/health",
                      headers=headers_u2_srvA).status_code == 200

    # user-3 en srv-A NO bloqueado
    assert client.get("/api/v1/servers/srv-A/health",
                      headers={"X-User-Id": "user-3"}).status_code == 200


# ---------------------------------------------------------------------------
# T-44.1-3: Ad-hoc exec — superar límite devuelve 429 con Retry-After
# ---------------------------------------------------------------------------


def test_exec_rate_limit_returns_429_after_limit(client: TestClient) -> None:
    """Superar 30 req/hora en exec devuelve 429 con Retry-After."""
    headers = {"X-User-Id": "user-exec-1"}
    for _ in range(30):
        resp = client.post("/api/v1/servers/srv-1/exec", headers=headers)
        assert resp.status_code == 200

    resp = client.post("/api/v1/servers/srv-1/exec", headers=headers)
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


# ---------------------------------------------------------------------------
# T-44.1-4: Rutas no sujetas a rate limit pasan libremente
# ---------------------------------------------------------------------------


def test_non_rate_limited_route_always_passes(client: TestClient) -> None:
    """Rutas sin rate limit (ej. listado de servidores) no son bloqueadas."""
    headers = {"X-User-Id": "user-list"}
    for _ in range(50):
        resp = client.get("/api/v1/servers", headers=headers)
        assert resp.status_code == 200
