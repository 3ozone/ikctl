"""Tests de presentación — GET /api/v1/groups/{id} (T-60).

Verifica que el endpoint de obtener grupo:
1. Devuelve 200 con GroupResponse cuando el grupo existe
2. Devuelve 404 cuando el grupo no existe o no pertenece al usuario
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.group_result import GroupResult
from app.v1.servers.domain.exceptions.group import GroupNotFoundError
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_get_group,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-group-get"
_GROUP_ID = "grp-get-001"
_NOW = datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeGetGroupOk:
    """Fake que devuelve un GroupResult."""

    async def execute(self, **kwargs) -> GroupResult:
        """Devuelve grupo encontrado."""
        return GroupResult(
            group_id=_GROUP_ID,
            user_id=_USER_ID,
            name="k8s-nodes",
            description="Nodos de Kubernetes",
            server_ids=["srv-001", "srv-002"],
            created_at=_NOW,
            updated_at=_NOW,
        )


class FakeGetGroupNotFound:
    """Fake que lanza GroupNotFoundError."""

    async def execute(self, **kwargs) -> GroupResult:
        """Lanza GroupNotFoundError."""
        raise GroupNotFoundError("Grupo no encontrado.")


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
def client_ok():
    """Cliente con use case que devuelve el grupo encontrado."""
    app.dependency_overrides[get_get_group] = lambda: FakeGetGroupOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_not_found():
    """Cliente con use case que lanza GroupNotFoundError."""
    app.dependency_overrides[get_get_group] = lambda: FakeGetGroupNotFound()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_group_returns_200(client_ok: TestClient) -> None:
    """GET /groups/{id} devuelve 200 con GroupResponse."""
    resp = client_ok.get(f"/api/v1/groups/{_GROUP_ID}", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["group_id"] == _GROUP_ID
    assert data["user_id"] == _USER_ID
    assert data["name"] == "k8s-nodes"
    assert len(data["server_ids"]) == 2


def test_get_group_not_found_returns_404(client_not_found: TestClient) -> None:
    """GET /groups/{id} devuelve 404 cuando el grupo no existe."""
    resp = client_not_found.get(f"/api/v1/groups/{_GROUP_ID}", headers=_auth_headers())
    assert resp.status_code == 404
    assert "detail" in resp.json()
