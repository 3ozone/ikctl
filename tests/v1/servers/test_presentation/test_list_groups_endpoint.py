"""Tests de presentación — GET /api/v1/groups (T-59).

Verifica que el endpoint de listar grupos:
1. Devuelve 200 con GroupListResponse con items cuando hay grupos
2. Devuelve 200 con lista vacía cuando el usuario no tiene grupos
3. Respeta los parámetros de paginación (page, per_page)
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.group_list_result import GroupListResult
from app.v1.servers.application.dtos.group_result import GroupResult
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_list_groups,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-group-list"
_NOW = datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc)


def _make_group(group_id: str, name: str) -> GroupResult:
    """Construye un GroupResult de prueba."""
    return GroupResult(
        group_id=group_id,
        user_id=_USER_ID,
        name=name,
        description=None,
        server_ids=["srv-001"],
        created_at=_NOW,
        updated_at=_NOW,
    )


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeListGroupsWithItems:
    """Fake que devuelve dos grupos."""

    async def execute(self, user_id: str, page: int, per_page: int) -> GroupListResult:
        """Devuelve lista con 2 grupos."""
        items = [
            _make_group("grp-001", "k8s-nodes"),
            _make_group("grp-002", "db-servers"),
        ]
        return GroupListResult(items=items, total=2, page=page, per_page=per_page)


class FakeListGroupsEmpty:
    """Fake que devuelve lista vacía."""

    async def execute(self, user_id: str, page: int, per_page: int) -> GroupListResult:
        """Devuelve lista vacía."""
        return GroupListResult(items=[], total=0, page=page, per_page=per_page)


class FakeListGroupsPaginated:
    """Fake que respeta page y per_page en la respuesta."""

    async def execute(self, user_id: str, page: int, per_page: int) -> GroupListResult:
        """Devuelve respuesta con los parámetros de paginación recibidos."""
        return GroupListResult(
            items=[_make_group("grp-001", "k8s-nodes")],
            total=10,
            page=page,
            per_page=per_page,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_headers() -> dict:
    """Genera cabeceras de autenticación JWT para _USER_ID."""
    token = jwt_provider.create_access_token(user_id=_USER_ID).token
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client_with_items():
    """Cliente con use case que devuelve 2 grupos."""
    app.dependency_overrides[get_list_groups] = lambda: FakeListGroupsWithItems()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_empty():
    """Cliente con use case que devuelve lista vacía."""
    app.dependency_overrides[get_list_groups] = lambda: FakeListGroupsEmpty()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_paginated():
    """Cliente con use case que respeta parámetros de paginación."""
    app.dependency_overrides[get_list_groups] = lambda: FakeListGroupsPaginated()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_list_groups_returns_200_with_items(client_with_items: TestClient) -> None:
    """GET /groups devuelve 200 con lista de grupos."""
    resp = client_with_items.get("/api/v1/groups", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 2
    assert data["items"][0]["group_id"] == "grp-001"
    assert data["items"][1]["group_id"] == "grp-002"


def test_list_groups_returns_200_empty(client_empty: TestClient) -> None:
    """GET /groups devuelve 200 con lista vacía cuando no hay grupos."""
    resp = client_empty.get("/api/v1/groups", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_groups_pagination_params(client_paginated: TestClient) -> None:
    """GET /groups respeta los parámetros page y per_page."""
    resp = client_paginated.get(
        "/api/v1/groups",
        params={"page": 2, "per_page": 5},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
    assert data["per_page"] == 5
    assert data["total"] == 10
