"""Tests de presentación — endpoints /api/v1/pipelines (T-37).

Verifica:
1. POST   /api/v1/pipelines                              → 201 crear pipeline
2. GET    /api/v1/pipelines                              → 200 lista paginada
3. GET    /api/v1/pipelines/{id}                         → 200 detalle
4. PUT    /api/v1/pipelines/{id}                         → 200 actualizar
5. DELETE /api/v1/pipelines/{id}                         → 204 eliminar
6. POST   /api/v1/pipelines/{id}/executions              → 201 lanzar ejecución
7. GET    /api/v1/pipelines/{id}/executions              → 200 lista ejecuciones
8. GET    /api/v1/pipelines/{id}/executions/{exec_id}    → 200 detalle ejecución
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.pipelines.application.dtos.pipeline_dtos import (
    PipelineExecutionDetailResult,
    PipelineExecutionListResult,
    PipelineExecutionResult,
    PipelineExecutionSummary,
    PipelineListResult,
    PipelineOperationItem,
    PipelineResult,
)
from app.v1.pipelines.application.exceptions import (
    LocalServerInPipelineError,
    PipelineInProgressError,
    PipelineNotLaunchableError,
)
from app.v1.pipelines.domain.exceptions.pipeline import PipelineNotFoundError
from app.v1.pipelines.domain.exceptions.pipeline_execution import (
    PipelineExecutionNotFoundError,
)
from app.v1.pipelines.infrastructure.presentation.deps import (
    get_create_pipeline_uc,
    get_current_user_id,
    get_delete_pipeline_uc,
    get_get_pipeline_execution_detail_uc,
    get_get_pipeline_executions_uc,
    get_get_pipeline_uc,
    get_launch_pipeline_uc,
    get_list_pipelines_uc,
    get_update_pipeline_uc,
)
from main import app, jwt_provider

_USER_ID = "user-pipelines-ep"
_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

_PIPELINE_RESULT = PipelineResult(
    pipeline_id="pipe-001",
    user_id=_USER_ID,
    name="Mi Pipeline",
    description="desc",
    targets=({"server_id": "srv-1"},),
    kits=({"kit_id": "kit-1", "sudo": None, "debug_level": None},),
    values={},
    sudo=False,
    debug_level="none",
    created_at=_NOW,
    updated_at=_NOW,
)

_PIPELINE_LIST = PipelineListResult(
    items=(_PIPELINE_RESULT,),
    total=1,
    page=1,
    per_page=50,
)

_EXEC_RESULT = PipelineExecutionResult(
    execution_id="exec-001",
    pipeline_id="pipe-001",
    user_id=_USER_ID,
    status="pending",
    snapshot={"targets": [{"server_id": "srv-1"}], "kits": [{"kit_id": "kit-1"}]},
    created_at=_NOW,
)

_EXEC_SUMMARY = PipelineExecutionSummary(
    execution_id="exec-001",
    pipeline_id="pipe-001",
    status="pending",
    total_operations=1,
    completed_operations=0,
    failed_operations=0,
    created_at=_NOW,
    started_at=None,
    finished_at=None,
)

_EXEC_LIST = PipelineExecutionListResult(
    items=(_EXEC_SUMMARY,),
    total=1,
    page=1,
    per_page=50,
)

_EXEC_DETAIL = PipelineExecutionDetailResult(
    execution_id="exec-001",
    pipeline_id="pipe-001",
    user_id=_USER_ID,
    status="completed",
    snapshot={"targets": [{"server_id": "srv-1"}], "kits": [{"kit_id": "kit-1"}]},
    operations=(
        PipelineOperationItem(
            operation_id="op-1",
            server_id="srv-1",
            kit_id="kit-1",
            status="completed",
            output="",
            error=None,
        ),
    ),
    created_at=_NOW,
    started_at=_NOW,
    finished_at=_NOW,
)


# ---------------------------------------------------------------------------
# Fake use cases
# ---------------------------------------------------------------------------


class FakeCreateOk:
    async def execute(self, **kwargs) -> PipelineResult:
        return _PIPELINE_RESULT


class FakeCreateLocalServer:
    async def execute(self, **kwargs) -> PipelineResult:
        raise LocalServerInPipelineError("Servidor local no permitido.")


class FakeListOk:
    async def execute(self, **kwargs) -> PipelineListResult:
        return _PIPELINE_LIST


class FakeGetOk:
    async def execute(self, **kwargs) -> PipelineResult:
        return _PIPELINE_RESULT


class FakeGetNotFound:
    async def execute(self, **kwargs) -> PipelineResult:
        raise PipelineNotFoundError("Pipeline no encontrado.")


class FakeUpdateOk:
    async def execute(self, **kwargs) -> PipelineResult:
        return _PIPELINE_RESULT


class FakeUpdateConflict:
    async def execute(self, **kwargs) -> PipelineResult:
        raise PipelineInProgressError("Pipeline tiene ejecuciones activas.")


class FakeDeleteOk:
    async def execute(self, **kwargs) -> None:
        pass


class FakeDeleteConflict:
    async def execute(self, **kwargs) -> None:
        raise PipelineInProgressError("Pipeline tiene ejecuciones activas.")


class FakeLaunchOk:
    async def execute(self, **kwargs) -> PipelineExecutionResult:
        return _EXEC_RESULT


class FakeLaunchNotLaunchable:
    async def execute(self, **kwargs) -> PipelineExecutionResult:
        raise PipelineNotLaunchableError("Kit no usable.")


class FakeExecutionsOk:
    async def execute(self, **kwargs) -> PipelineExecutionListResult:
        return _EXEC_LIST


class FakeDetailOk:
    async def execute(self, **kwargs) -> PipelineExecutionDetailResult:
        return _EXEC_DETAIL


class FakeDetailNotFound:
    async def execute(self, **kwargs) -> PipelineExecutionDetailResult:
        raise PipelineExecutionNotFoundError("Ejecución no encontrada.")


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
def client_create_ok():
    app.dependency_overrides[get_create_pipeline_uc] = lambda: FakeCreateOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_create_local_server():
    app.dependency_overrides[get_create_pipeline_uc] = lambda: FakeCreateLocalServer()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_list_ok():
    app.dependency_overrides[get_list_pipelines_uc] = lambda: FakeListOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_get_ok():
    app.dependency_overrides[get_get_pipeline_uc] = lambda: FakeGetOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_get_not_found():
    app.dependency_overrides[get_get_pipeline_uc] = lambda: FakeGetNotFound()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_update_ok():
    app.dependency_overrides[get_update_pipeline_uc] = lambda: FakeUpdateOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_update_conflict():
    app.dependency_overrides[get_update_pipeline_uc] = lambda: FakeUpdateConflict()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_delete_ok():
    app.dependency_overrides[get_delete_pipeline_uc] = lambda: FakeDeleteOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_delete_conflict():
    app.dependency_overrides[get_delete_pipeline_uc] = lambda: FakeDeleteConflict()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_launch_ok():
    app.dependency_overrides[get_launch_pipeline_uc] = lambda: FakeLaunchOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_launch_not_launchable():
    app.dependency_overrides[get_launch_pipeline_uc] = lambda: FakeLaunchNotLaunchable()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_executions_ok():
    app.dependency_overrides[get_get_pipeline_executions_uc] = lambda: FakeExecutionsOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_detail_ok():
    app.dependency_overrides[get_get_pipeline_execution_detail_uc] = lambda: FakeDetailOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_detail_not_found():
    app.dependency_overrides[get_get_pipeline_execution_detail_uc] = lambda: FakeDetailNotFound()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_pipeline_returns_201(client_create_ok: TestClient) -> None:
    resp = client_create_ok.post(
        "/api/v1/pipelines",
        json={
            "name": "Mi Pipeline",
            "targets": [{"server_id": "srv-1"}],
            "kits": [{"kit_id": "kit-1"}],
        },
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["pipeline_id"] == "pipe-001"
    assert data["name"] == "Mi Pipeline"
    assert len(data["targets"]) == 1
    assert data["targets"][0]["server_id"] == "srv-1"


def test_create_pipeline_local_server_returns_422(client_create_local_server: TestClient) -> None:
    resp = client_create_local_server.post(
        "/api/v1/pipelines",
        json={
            "name": "Bad",
            "targets": [{"server_id": "local-1"}],
            "kits": [{"kit_id": "kit-1"}],
        },
        headers=_auth_headers(),
    )
    assert resp.status_code == 422
    assert "local" in resp.json()["detail"].lower()


def test_list_pipelines_returns_200(client_list_ok: TestClient) -> None:
    resp = client_list_ok.get("/api/v1/pipelines", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["pipeline_id"] == "pipe-001"


def test_get_pipeline_returns_200(client_get_ok: TestClient) -> None:
    resp = client_get_ok.get(f"/api/v1/pipelines/pipe-001", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["pipeline_id"] == "pipe-001"


def test_get_pipeline_not_found_returns_404(client_get_not_found: TestClient) -> None:
    resp = client_get_not_found.get(f"/api/v1/pipelines/nope", headers=_auth_headers())
    assert resp.status_code == 404


def test_update_pipeline_returns_200(client_update_ok: TestClient) -> None:
    resp = client_update_ok.put(
        f"/api/v1/pipelines/pipe-001",
        json={"name": "Updated"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["pipeline_id"] == "pipe-001"


def test_update_pipeline_conflict_returns_409(client_update_conflict: TestClient) -> None:
    resp = client_update_conflict.put(
        f"/api/v1/pipelines/pipe-001",
        json={"name": "Updated"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 409


def test_delete_pipeline_returns_204(client_delete_ok: TestClient) -> None:
    resp = client_delete_ok.delete(
        f"/api/v1/pipelines/pipe-001",
        headers=_auth_headers(),
    )
    assert resp.status_code == 204


def test_delete_pipeline_conflict_returns_409(client_delete_conflict: TestClient) -> None:
    resp = client_delete_conflict.delete(
        f"/api/v1/pipelines/pipe-001",
        headers=_auth_headers(),
    )
    assert resp.status_code == 409


def test_launch_pipeline_returns_201(client_launch_ok: TestClient) -> None:
    resp = client_launch_ok.post(
        f"/api/v1/pipelines/pipe-001/executions",
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["execution_id"] == "exec-001"
    assert data["status"] == "pending"
    assert "snapshot" in data


def test_launch_pipeline_not_launchable_returns_422(client_launch_not_launchable: TestClient) -> None:
    resp = client_launch_not_launchable.post(
        f"/api/v1/pipelines/pipe-001/executions",
        headers=_auth_headers(),
    )
    assert resp.status_code == 422


def test_get_executions_returns_200(client_executions_ok: TestClient) -> None:
    resp = client_executions_ok.get(
        f"/api/v1/pipelines/pipe-001/executions",
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["execution_id"] == "exec-001"


def test_get_execution_detail_returns_200(client_detail_ok: TestClient) -> None:
    resp = client_detail_ok.get(
        f"/api/v1/pipelines/pipe-001/executions/exec-001",
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["execution_id"] == "exec-001"
    assert data["status"] == "completed"
    assert len(data["operations"]) == 1
    assert data["operations"][0]["operation_id"] == "op-1"


def test_get_execution_detail_not_found_returns_404(client_detail_not_found: TestClient) -> None:
    resp = client_detail_not_found.get(
        f"/api/v1/pipelines/pipe-001/executions/nope",
        headers=_auth_headers(),
    )
    assert resp.status_code == 404