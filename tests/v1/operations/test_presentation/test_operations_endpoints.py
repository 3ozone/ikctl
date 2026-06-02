"""Tests de presentación — endpoints /api/v1/operations (T-34).

Verifica:
1. POST   /api/v1/operations              → 201 pending  (lanzar OK)
2. GET    /api/v1/operations              → 200 lista paginada
3. GET    /api/v1/operations/{id}         → 200 detalle
4. POST   /api/v1/operations/{id}/cancel  → 200 cancelled
5. POST   /api/v1/operations/{id}/cancel  → 409 si transición inválida
6. POST   /api/v1/operations              → 422 si servidor inactivo
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.operations.application.dtos.operation_dtos import (
    OperationListResult,
    OperationResult,
    RestoreResult,
)
from app.v1.operations.application.exceptions import ServerNotActiveError
from app.v1.operations.domain.exceptions.operation import (
    InvalidOperationTransitionError,
    OperationNotFoundError,
)
from app.v1.operations.infrastructure.presentation.deps import (
    get_cancel_operation_uc,
    get_current_user_id,
    get_get_operation_uc,
    get_launch_operation_uc,
    get_list_operations_uc,
    get_restore_operation_backup_uc,
    get_retry_operation_uc,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes compartidas
# ---------------------------------------------------------------------------

_USER_ID = "user-ops-endpoints"
_SERVER_ID = "server-001"
_KIT_ID = "kit-001"
_OP_ID = "op-001"
_NEW_OP_ID = "op-002"
_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

_OP_RESULT = OperationResult(
    operation_id=_OP_ID,
    user_id=_USER_ID,
    server_id=_SERVER_ID,
    kit_id=_KIT_ID,
    values={},
    sudo=False,
    status="pending",
    debug_level="none",
    output="",
    backup_files=(),
    created_at=_NOW,
    updated_at=_NOW,
    started_at=None,
    finished_at=None,
)

_OP_CANCELLED = OperationResult(
    operation_id=_OP_ID,
    user_id=_USER_ID,
    server_id=_SERVER_ID,
    kit_id=_KIT_ID,
    values={},
    sudo=False,
    status="cancelled",
    debug_level="none",
    output="",
    backup_files=(),
    created_at=_NOW,
    updated_at=_NOW,
    started_at=None,
    finished_at=None,
)

_OP_LIST_RESULT = OperationListResult(
    items=(_OP_RESULT,),
    total=1,
    page=1,
    per_page=50,
)

_RESTORE_RESULT = RestoreResult(
    operation_id=_OP_ID,
    restored_files=("/etc/nginx/nginx.conf.bak.ikctl",),
)

_OP_RETRY_RESULT = OperationResult(
    operation_id=_NEW_OP_ID,
    user_id=_USER_ID,
    server_id=_SERVER_ID,
    kit_id=_KIT_ID,
    values={"port": 8080},
    sudo=True,
    status="pending",
    debug_level="none",
    output="",
    backup_files=(),
    created_at=_NOW,
    updated_at=_NOW,
    started_at=None,
    finished_at=None,
)


# ---------------------------------------------------------------------------
# Fake use cases
# ---------------------------------------------------------------------------


class FakeLaunchOk:
    async def execute(self, **kwargs) -> OperationResult:
        return _OP_RESULT


class FakeLaunchServerInactive:
    async def execute(self, **kwargs) -> OperationResult:
        raise ServerNotActiveError("El servidor está inactivo.")


class FakeListOk:
    async def execute(self, **kwargs) -> OperationListResult:
        return _OP_LIST_RESULT


class FakeGetOk:
    async def execute(self, **kwargs) -> OperationResult:
        return _OP_RESULT


class FakeGetNotFound:
    async def execute(self, **kwargs) -> OperationResult:
        raise OperationNotFoundError("Operación no encontrada.")


class FakeCancelOk:
    async def execute(self, **kwargs) -> OperationResult:
        return _OP_CANCELLED


class FakeCancelInvalidTransition:
    async def execute(self, **kwargs) -> OperationResult:
        raise InvalidOperationTransitionError("No se puede cancelar: ya está en estado terminal.")


class FakeRestoreOk:
    async def execute(self, **kwargs) -> RestoreResult:
        return _RESTORE_RESULT


class FakeRetryOk:
    async def execute(self, **kwargs) -> OperationResult:
        return _OP_RETRY_RESULT


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
def client_launch_ok():
    app.dependency_overrides[get_launch_operation_uc] = lambda: FakeLaunchOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_launch_inactive_server():
    app.dependency_overrides[get_launch_operation_uc] = lambda: FakeLaunchServerInactive()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_list_ok():
    app.dependency_overrides[get_list_operations_uc] = lambda: FakeListOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_get_ok():
    app.dependency_overrides[get_get_operation_uc] = lambda: FakeGetOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_get_not_found():
    app.dependency_overrides[get_get_operation_uc] = lambda: FakeGetNotFound()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_cancel_ok():
    app.dependency_overrides[get_cancel_operation_uc] = lambda: FakeCancelOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_cancel_conflict():
    app.dependency_overrides[get_cancel_operation_uc] = lambda: FakeCancelInvalidTransition()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_restore_ok():
    app.dependency_overrides[get_restore_operation_backup_uc] = lambda: FakeRestoreOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_retry_ok():
    app.dependency_overrides[get_retry_operation_uc] = lambda: FakeRetryOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# T-28: POST /api/v1/operations — lanzar operación
# ---------------------------------------------------------------------------


def test_launch_operation_returns_201(client_launch_ok: TestClient) -> None:
    """POST /api/v1/operations devuelve 201 con estado pending."""
    resp = client_launch_ok.post(
        "/api/v1/operations",
        json={"server_id": _SERVER_ID, "kit_id": _KIT_ID},
        headers=_auth_headers(),
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["operation_id"] == _OP_ID
    assert data["status"] == "pending"
    assert data["server_id"] == _SERVER_ID
    assert data["kit_id"] == _KIT_ID


def test_launch_inactive_server_returns_422(client_launch_inactive_server: TestClient) -> None:
    """POST /api/v1/operations devuelve 422 si el servidor está inactivo."""
    resp = client_launch_inactive_server.post(
        "/api/v1/operations",
        json={"server_id": _SERVER_ID, "kit_id": _KIT_ID},
        headers=_auth_headers(),
    )

    assert resp.status_code == 422
    assert "inactivo" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# T-29: GET /api/v1/operations — listar operaciones
# ---------------------------------------------------------------------------


def test_list_operations_returns_200(client_list_ok: TestClient) -> None:
    """GET /api/v1/operations devuelve 200 con lista paginada."""
    resp = client_list_ok.get("/api/v1/operations", headers=_auth_headers())

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["operation_id"] == _OP_ID


# ---------------------------------------------------------------------------
# T-30: GET /api/v1/operations/{id} — consultar estado
# ---------------------------------------------------------------------------


def test_get_operation_returns_200(client_get_ok: TestClient) -> None:
    """GET /api/v1/operations/{id} devuelve 200 con el detalle."""
    resp = client_get_ok.get(f"/api/v1/operations/{_OP_ID}", headers=_auth_headers())

    assert resp.status_code == 200
    data = resp.json()
    assert data["operation_id"] == _OP_ID
    assert data["status"] == "pending"


def test_get_operation_not_found_returns_404(client_get_not_found: TestClient) -> None:
    """GET /api/v1/operations/{id} devuelve 404 si no existe."""
    resp = client_get_not_found.get(f"/api/v1/operations/{_OP_ID}", headers=_auth_headers())

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# T-31: POST /api/v1/operations/{id}/cancel — cancelar operación
# ---------------------------------------------------------------------------


def test_cancel_operation_returns_200(client_cancel_ok: TestClient) -> None:
    """POST /api/v1/operations/{id}/cancel devuelve 200 con estado cancelled."""
    resp = client_cancel_ok.post(
        f"/api/v1/operations/{_OP_ID}/cancel",
        headers=_auth_headers(),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["operation_id"] == _OP_ID
    assert data["status"] == "cancelled"


def test_cancel_terminal_operation_returns_409(client_cancel_conflict: TestClient) -> None:
    """POST /api/v1/operations/{id}/cancel devuelve 409 si la transición no es válida."""
    resp = client_cancel_conflict.post(
        f"/api/v1/operations/{_OP_ID}/cancel",
        headers=_auth_headers(),
    )

    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# T-32: POST /api/v1/operations/{id}/restore — restaurar backup
# ---------------------------------------------------------------------------


def test_restore_operation_returns_200(client_restore_ok: TestClient) -> None:
    """POST /api/v1/operations/{id}/restore devuelve 200 con archivos restaurados."""
    resp = client_restore_ok.post(
        f"/api/v1/operations/{_OP_ID}/restore",
        headers=_auth_headers(),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["operation_id"] == _OP_ID
    assert len(data["restored_files"]) == 1


# ---------------------------------------------------------------------------
# T-33: POST /api/v1/operations/{id}/retry — reintentar operación
# ---------------------------------------------------------------------------


def test_retry_operation_returns_201(client_retry_ok: TestClient) -> None:
    """POST /api/v1/operations/{id}/retry devuelve 201 con nueva operación pending."""
    resp = client_retry_ok.post(
        f"/api/v1/operations/{_OP_ID}/retry",
        headers=_auth_headers(),
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["operation_id"] == _NEW_OP_ID
    assert data["status"] == "pending"
