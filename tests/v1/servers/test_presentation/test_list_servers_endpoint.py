"""Tests de presentación — GET /api/v1/servers (T-51).

Verifica que el endpoint de listado de servidores:
1. Devuelve 200 con lista paginada cuando hay servidores
2. Devuelve 200 con lista vacía cuando no hay servidores
3. Respeta los parámetros de paginación page y per_page
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.server_list_result import ServerListResult
from app.v1.servers.application.dtos.server_result import ServerResult
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_list_servers,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-list-servers"
_NOW = datetime(2026, 3, 31, 12, 0, 0, tzinfo=timezone.utc)

_SERVER_RESULT = ServerResult(
    server_id="srv-001",
    user_id=_USER_ID,
    name="web-01",
    server_type="remote",
    status="active",
    host="192.168.1.10",
    port=22,
    credential_id="cred-abc",
    description=None,
    os_id=None,
    os_version=None,
    os_name=None,
    created_at=_NOW,
    updated_at=_NOW,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeListServersWithItems:
    """Fake que devuelve una lista con un servidor."""

    async def execute(self, user_id: str, page: int, per_page: int) -> ServerListResult:
        return ServerListResult(items=[_SERVER_RESULT], total=1, page=page, per_page=per_page)


class FakeListServersEmpty:
    """Fake que devuelve lista vacía."""

    async def execute(self, user_id: str, page: int, per_page: int) -> ServerListResult:
        return ServerListResult(items=[], total=0, page=page, per_page=per_page)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_headers() -> dict:
    token = jwt_provider.create_access_token(user_id=_USER_ID).token
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client_with_items():
    """Client con use case que devuelve lista con un servidor."""
    app.dependency_overrides[get_list_servers] = lambda: FakeListServersWithItems(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_empty():
    """Client con use case que devuelve lista vacía."""
    app.dependency_overrides[get_list_servers] = lambda: FakeListServersEmpty()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_list_servers_returns_200_with_items(client_with_items: TestClient) -> None:
    """GET /servers devuelve 200 con lista paginada."""
    resp = client_with_items.get("/api/v1/servers", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["server_id"] == "srv-001"
    assert data["items"][0]["server_type"] == "remote"


def test_list_servers_returns_200_empty(client_empty: TestClient) -> None:
    """GET /servers devuelve 200 con lista vacía."""
    resp = client_empty.get("/api/v1/servers", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_servers_pagination_params(client_with_items: TestClient) -> None:
    """GET /servers respeta los parámetros page y per_page."""
    resp = client_with_items.get(
        "/api/v1/servers", params={"page": 2, "per_page": 5}, headers=_auth_headers()
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
    assert data["per_page"] == 5
