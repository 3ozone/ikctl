"""Contract tests para FastAPITaskQueue — T-38.

Verifica que FastAPITaskQueue implementa el contrato del puerto TaskQueue:
  1. La tarea encolada se ejecuta efectivamente tras la respuesta HTTP.
  2. `enqueue` no bloquea el request: la respuesta se envía antes de que
     la tarea empiece a ejecutarse.

Se usa una mini-app FastAPI con TestClient para ejercitar el ciclo completo
de BackgroundTasks (enqueue → response → task execution).
"""
from fastapi import BackgroundTasks, FastAPI
from fastapi.testclient import TestClient

from app.v1.operations.infrastructure.adapters.fastapi_task_queue import FastAPITaskQueue


# ---------------------------------------------------------------------------
# Helpers de infraestructura para el contrato
# ---------------------------------------------------------------------------


def _make_test_app(events: list[str]) -> FastAPI:
    """Crea una mini-app FastAPI que encola una tarea de seguimiento.

    La task appends 'task_executed' a `events` cuando corre.
    El handler appends 'response_sent' a `events` justo antes de retornar,
    después de llamar a `enqueue`, para capturar el orden de ejecución.
    """
    test_app = FastAPI()

    async def _tracking_task(operation_id: str) -> None:
        events.append(f"task_executed:{operation_id}")

    @test_app.post("/run")
    async def _endpoint(background_tasks: BackgroundTasks):
        queue = FastAPITaskQueue(background_tasks)
        await queue.enqueue(_tracking_task, "op-contract-1")
        # Este append ocurre ANTES de que BackgroundTasks ejecute la task
        events.append("response_sent")
        return {"status": "queued"}

    return test_app


# ---------------------------------------------------------------------------
# T-38.1 — La tarea se ejecuta efectivamente
# ---------------------------------------------------------------------------


def test_task_is_executed_after_response() -> None:
    """La función encolada via FastAPITaskQueue es llamada tras la respuesta."""
    events: list[str] = []
    client = TestClient(_make_test_app(events))

    resp = client.post("/run")

    assert resp.status_code == 200
    assert resp.json() == {"status": "queued"}
    # La task debe haber corrido (BackgroundTasks se ejecutan antes de que
    # TestClient devuelva el control)
    assert "task_executed:op-contract-1" in events


# ---------------------------------------------------------------------------
# T-38.2 — `enqueue` no bloquea el request (response antes que task)
# ---------------------------------------------------------------------------


def test_enqueue_does_not_block_response() -> None:
    """La respuesta HTTP se envía antes de que la tarea empiece a ejecutarse."""
    events: list[str] = []
    client = TestClient(_make_test_app(events))

    client.post("/run")

    # El orden debe ser: response_sent → task_executed
    assert "response_sent" in events
    assert "task_executed:op-contract-1" in events
    assert events.index("response_sent") < events.index("task_executed:op-contract-1"), (
        f"Se esperaba 'response_sent' antes que 'task_executed'. "
        f"Orden real: {events}"
    )
