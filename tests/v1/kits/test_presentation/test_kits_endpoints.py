"""Tests de presentación — endpoints /api/v1/kits (T-38).

Verifica:
1. GET /api/v1/kits              → 200 lista paginada OK
2. GET /api/v1/kits?repository_id → 200 filtrado por repositorio
3. GET /api/v1/kits/{id}         → 200 detalle del kit
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.kits.application.dtos.kit_list_result import KitListResult
from app.v1.kits.application.dtos.kit_result import KitResult
from app.v1.kits.application.exceptions import KitNotFoundError
from app.v1.kits.infrastructure.presentation.deps import (
    get_current_user_id,
    get_get_kit_uc,
    get_list_kits_uc,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-kits-endpoints"
_REPO_ID = "repo-kits-001"
_KIT_ID = "kit-001"
_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

_KIT_RESULT = KitResult(
    kit_id=_KIT_ID,
    user_id=_USER_ID,
    repository_id=_REPO_ID,
    path_in_repo="nginx",
    name="nginx-kit",
    description="Kit para instalar NGINX",
    version="1.0.0",
    tags=["web", "proxy"],
    values={"port": 80},
    debug_level="info",
    sync_status="synced",
    last_synced_at=_NOW,
    last_commit_sha="abc123",
    sync_error_message=None,
    created_at=_NOW,
    updated_at=_NOW,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeListKitsOk:
    async def execute(self, **kwargs) -> KitListResult:
        return KitListResult(items=[_KIT_RESULT], total=1, page=1, per_page=50)


class FakeListKitsFilteredByRepo:
    """Captura kwargs para verificar que repository_id_filter se propaga."""

    def __init__(self) -> None:
        self.captured_kwargs: dict = {}

    async def execute(self, **kwargs) -> KitListResult:
        self.captured_kwargs = kwargs
        return KitListResult(items=[_KIT_RESULT], total=1, page=1, per_page=50)


class FakeGetKitOk:
    async def execute(self, **kwargs) -> KitResult:
        return _KIT_RESULT


class FakeGetKitNotFound:
    async def execute(self, **kwargs) -> KitResult:
        raise KitNotFoundError("Kit no encontrado.")


# ---------------------------------------------------------------------------
# Helper auth
# ---------------------------------------------------------------------------


def _auth_headers() -> dict:
    token = jwt_provider.create_access_token(
        user_id=_USER_ID,
        additional_claims={"role": "user"},
    ).token
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client_list_kits_ok():
    app.dependency_overrides[get_list_kits_uc] = lambda: FakeListKitsOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def fake_list_kits_filtered():
    return FakeListKitsFilteredByRepo()


@pytest.fixture()
def client_list_kits_filtered(fake_list_kits_filtered: FakeListKitsFilteredByRepo):
    app.dependency_overrides[get_list_kits_uc] = lambda: fake_list_kits_filtered
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_get_kit_ok():
    app.dependency_overrides[get_get_kit_uc] = lambda: FakeGetKitOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_get_kit_not_found():
    app.dependency_overrides[get_get_kit_uc] = lambda: FakeGetKitNotFound()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — T-35: GET /api/v1/kits
# ---------------------------------------------------------------------------


def test_list_kits_returns_200(client_list_kits_ok: TestClient) -> None:
    """GET /api/v1/kits devuelve 200 con lista paginada."""
    resp = client_list_kits_ok.get("/api/v1/kits", headers=_auth_headers())

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["kit_id"] == _KIT_ID
    assert item["repository_id"] == _REPO_ID
    assert item["sync_status"] == "synced"
    assert item["tags"] == ["web", "proxy"]


def test_list_kits_filter_by_repository_id_returns_200(
    client_list_kits_filtered: TestClient,
    fake_list_kits_filtered: FakeListKitsFilteredByRepo,
) -> None:
    """GET /api/v1/kits?repository_id=X devuelve 200 con kits filtrados por repositorio."""
    resp = client_list_kits_filtered.get(
        f"/api/v1/kits?repository_id={_REPO_ID}", headers=_auth_headers()
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["repository_id"] == _REPO_ID
    # Verificar que el filtro se propagó al use case
    assert fake_list_kits_filtered.captured_kwargs.get("repository_id_filter") == _REPO_ID


# ---------------------------------------------------------------------------
# Tests — T-36: GET /api/v1/kits/{id}
# ---------------------------------------------------------------------------


def test_get_kit_returns_200(client_get_kit_ok: TestClient) -> None:
    """GET /api/v1/kits/{id} devuelve 200 con el detalle del kit."""
    resp = client_get_kit_ok.get(f"/api/v1/kits/{_KIT_ID}", headers=_auth_headers())

    assert resp.status_code == 200
    data = resp.json()
    assert data["kit_id"] == _KIT_ID
    assert data["name"] == "nginx-kit"
    assert data["version"] == "1.0.0"
    assert data["path_in_repo"] == "nginx"
    assert data["last_commit_sha"] == "abc123"
