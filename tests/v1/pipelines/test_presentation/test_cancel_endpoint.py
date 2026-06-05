"""Tests de presentación — endpoint POST .../cancel (R1, R5, R6, R7)."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.v1.pipelines.application.dtos.pipeline_dtos import PipelineExecutionCancelDTO
from app.v1.pipelines.domain.exceptions.pipeline import PipelineNotFoundError
from app.v1.pipelines.domain.exceptions.pipeline_execution import (
    PipelineExecutionNotCancellableError,
)
from app.v1.pipelines.infrastructure.presentation.deps import (
    get_cancel_pipeline_execution_uc,
    get_current_user_id,
)
from main import app, jwt_provider

_USER_ID = "user-cancel-ep"
_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

_CANCEL_DTO = PipelineExecutionCancelDTO(
    execution_id="exec-001",
    pipeline_id="pipe-001",
    user_id=_USER_ID,
    status="cancelled",
    finished_at=_NOW,
)


class FakeCancelOk:
    async def execute(self, **kwargs):
        return _CANCEL_DTO


class FakeCancelPending:
    async def execute(self, **kwargs):
        raise PipelineExecutionNotCancellableError(
            "No se puede cancelar una ejecución en estado 'pending'. "
            "Debe estar en estado 'in_progress'."
        )


class FakeCancelTerminal:
    async def execute(self, **kwargs):
        raise PipelineExecutionNotCancellableError(
            "No se puede cancelar una ejecución en estado 'completed'. "
            "Debe estar en estado 'in_progress'."
        )


class FakeCancelNotOwner:
    async def execute(self, **kwargs):
        raise PipelineNotFoundError(
            "Pipeline 'pipe-x' no encontrado o no pertenece al usuario."
        )


def _auth_headers() -> dict:
    token = jwt_provider.create_access_token(
        user_id=_USER_ID,
        additional_claims={"role": "user"},
    ).token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client_cancel_ok():
    app.dependency_overrides[get_cancel_pipeline_execution_uc] = lambda: FakeCancelOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_cancel_pending():
    app.dependency_overrides[get_cancel_pipeline_execution_uc] = lambda: FakeCancelPending()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_cancel_terminal():
    app.dependency_overrides[get_cancel_pipeline_execution_uc] = lambda: FakeCancelTerminal()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_cancel_not_owner():
    app.dependency_overrides[get_cancel_pipeline_execution_uc] = lambda: FakeCancelNotOwner()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_cancel_in_progress_returns_200(client_cancel_ok: TestClient) -> None:
    """R1: cancelar una ejecución in_progress devuelve 200."""
    resp = client_cancel_ok.post(
        f"/api/v1/pipelines/pipe-001/executions/exec-001/cancel",
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "cancelled"
    assert data["execution_id"] == "exec-001"


def test_cancel_pending_returns_422(client_cancel_pending: TestClient) -> None:
    """R6: cancelar una ejecución pending devuelve 422."""
    resp = client_cancel_pending.post(
        f"/api/v1/pipelines/pipe-001/executions/exec-001/cancel",
        headers=_auth_headers(),
    )
    assert resp.status_code == 422
    assert "pending" in resp.json()["detail"].lower() or "cancel" in resp.json()["detail"].lower()


def test_cancel_completed_returns_422(client_cancel_terminal: TestClient) -> None:
    """R5: cancelar una ejecución terminal devuelve 422."""
    resp = client_cancel_terminal.post(
        f"/api/v1/pipelines/pipe-001/executions/exec-001/cancel",
        headers=_auth_headers(),
    )
    assert resp.status_code == 422


def test_cancel_not_owner_returns_404(client_cancel_not_owner: TestClient) -> None:
    """R7: cancelar un pipeline ajeno devuelve 404."""
    resp = client_cancel_not_owner.post(
        f"/api/v1/pipelines/pipe-x/executions/exec-001/cancel",
        headers=_auth_headers(),
    )
    assert resp.status_code == 404