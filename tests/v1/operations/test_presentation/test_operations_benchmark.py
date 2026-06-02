"""Benchmark endpoints de consulta operations — T-37.

Verifica que los endpoints de consulta (GET /api/v1/operations y
GET /api/v1/operations/{id}) cumplen el SLO de latencia p99 < 200ms
con use cases en memoria (sin DB).

Referencia: RNF-01 — latencia CRUD < 200ms.
"""
import time
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.operations.application.dtos.operation_dtos import (
    OperationListResult,
    OperationResult,
)
from app.v1.operations.infrastructure.presentation.deps import (
    get_current_user_id,
    get_get_operation_uc,
    get_list_operations_uc,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-bench-ops"
_SERVER_ID = "server-bench"
_KIT_ID = "kit-bench"
_OP_ID = "op-bench-001"
_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
_N_REQUESTS = 50
_P99_THRESHOLD_MS = 200.0

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

_OP_LIST_RESULT = OperationListResult(
    items=(_OP_RESULT,),
    total=1,
    page=1,
    per_page=50,
)


# ---------------------------------------------------------------------------
# Fake use cases
# ---------------------------------------------------------------------------


class FakeGetOp:
    async def execute(self, **kwargs) -> OperationResult:
        return _OP_RESULT


class FakeListOps:
    async def execute(self, **kwargs) -> OperationListResult:
        return _OP_LIST_RESULT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_headers() -> dict:
    token = jwt_provider.create_access_token(
        user_id=_USER_ID,
        additional_claims={"role": "user"},
    ).token
    return {"Authorization": f"Bearer {token}"}


def _p99_ms(durations_ms: list[float]) -> float:
    """Calcula el percentil 99 de una lista de duraciones en ms."""
    sorted_d = sorted(durations_ms)
    idx = max(0, int(len(sorted_d) * 0.99) - 1)
    return sorted_d[idx]


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def bench_client():
    app.dependency_overrides[get_get_operation_uc] = lambda: FakeGetOp()
    app.dependency_overrides[get_list_operations_uc] = lambda: FakeListOps()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# T-37: Benchmark p99 < 200ms
# ---------------------------------------------------------------------------


def test_get_operation_p99_under_200ms(bench_client: TestClient) -> None:
    """GET /api/v1/operations/{id} — p99 de {N} requests < 200ms."""
    headers = _auth_headers()
    durations: list[float] = []

    for _ in range(_N_REQUESTS):
        t0 = time.perf_counter()
        resp = bench_client.get(f"/api/v1/operations/{_OP_ID}", headers=headers)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert resp.status_code == 200, f"Respuesta inesperada: {resp.status_code}"
        durations.append(elapsed_ms)

    p99 = _p99_ms(durations)
    assert p99 < _P99_THRESHOLD_MS, (
        f"GET /operations/{{id}} p99={p99:.1f}ms supera el SLO de {_P99_THRESHOLD_MS}ms"
    )


def test_list_operations_p99_under_200ms(bench_client: TestClient) -> None:
    """GET /api/v1/operations — p99 de {N} requests < 200ms."""
    headers = _auth_headers()
    durations: list[float] = []

    for _ in range(_N_REQUESTS):
        t0 = time.perf_counter()
        resp = bench_client.get("/api/v1/operations", headers=headers)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert resp.status_code == 200, f"Respuesta inesperada: {resp.status_code}"
        durations.append(elapsed_ms)

    p99 = _p99_ms(durations)
    assert p99 < _P99_THRESHOLD_MS, (
        f"GET /operations p99={p99:.1f}ms supera el SLO de {_P99_THRESHOLD_MS}ms"
    )
