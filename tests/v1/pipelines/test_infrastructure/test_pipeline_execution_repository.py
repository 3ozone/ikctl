"""Tests de integración para SQLAlchemyPipelineExecutionRepository — T-20."""
from datetime import datetime, timezone

import pytest

from app.v1.pipelines.domain.entities.pipeline_execution import PipelineExecution
from app.v1.pipelines.domain.value_objects.pipeline_status import PipelineStatus

# SQLite no preserva tzinfo en columnas DateTime — se usan datetimes naivos
NOW = datetime(2026, 1, 1, 12, 0, 0)
STARTED = datetime(2026, 1, 1, 12, 1, 0)
FINISHED = datetime(2026, 1, 1, 12, 5, 0)


def make_execution(
    execution_id: str = "exec-1",
    pipeline_id: str = "pipe-1",
    user_id: str = "user-1",
    status: str = "pending",
    operation_ids: list | None = None,
    snapshot: dict | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> PipelineExecution:
    return PipelineExecution(
        id=execution_id,
        pipeline_id=pipeline_id,
        user_id=user_id,
        status=PipelineStatus(status),
        operation_ids=operation_ids or [],
        snapshot=snapshot or {},
        created_at=NOW,
        started_at=started_at,
        finished_at=finished_at,
    )


# ---------------------------------------------------------------------------
# Test 1: save y find_by_id — roundtrip completo
# ---------------------------------------------------------------------------

async def test_save_and_find_by_id(execution_repository):
    """save persiste la ejecución y find_by_id la recupera con todos sus campos."""
    execution = make_execution(
        operation_ids=["op-1", "op-2"],
        snapshot={"targets": [{"server_id": "srv-1"}], "kits": []},
        started_at=STARTED,
        finished_at=FINISHED,
        status="completed",
    )
    await execution_repository.save(execution)

    found = await execution_repository.find_by_id("exec-1")

    assert found is not None
    assert found.id == "exec-1"
    assert found.pipeline_id == "pipe-1"
    assert found.user_id == "user-1"
    assert found.status == PipelineStatus("completed")
    assert found.operation_ids == ["op-1", "op-2"]
    assert found.snapshot == {"targets": [{"server_id": "srv-1"}], "kits": []}
    assert found.started_at == STARTED
    assert found.finished_at == FINISHED


async def test_find_by_id_nonexistent_returns_none(execution_repository):
    """find_by_id con id inexistente devuelve None."""
    assert await execution_repository.find_by_id("does-not-exist") is None


# ---------------------------------------------------------------------------
# Test 2: update — persiste cambios de estado, operation_ids, timestamps
# ---------------------------------------------------------------------------

async def test_update_persists_state_changes(execution_repository):
    """update persiste status, operation_ids, started_at, finished_at."""
    execution = make_execution()
    await execution_repository.save(execution)

    execution.start()
    execution.operation_ids = ["op-10", "op-11", "op-12"]
    await execution_repository.update(execution)

    refreshed = await execution_repository.find_by_id("exec-1")
    assert refreshed is not None
    assert refreshed.status == PipelineStatus("in_progress")
    assert refreshed.operation_ids == ["op-10", "op-11", "op-12"]
    assert refreshed.started_at is not None

    execution.mark_finished(["completed", "completed", "completed"])
    await execution_repository.update(execution)

    refreshed2 = await execution_repository.find_by_id("exec-1")
    assert refreshed2.status == PipelineStatus("completed")
    assert refreshed2.finished_at is not None


# ---------------------------------------------------------------------------
# Test 3: find_by_pipeline_id — paginación y scoping
# ---------------------------------------------------------------------------

async def test_find_by_pipeline_id_pagination(execution_repository):
    """find_by_pipeline_id devuelve las ejecuciones del pipeline, paginadas."""
    await execution_repository.save(make_execution("exec-1", "pipe-1"))
    await execution_repository.save(make_execution("exec-2", "pipe-1"))
    await execution_repository.save(make_execution("exec-3", "pipe-1"))
    await execution_repository.save(make_execution("exec-4", "pipe-2"))

    # Todas las de pipe-1
    result, total = await execution_repository.find_by_pipeline_id("pipe-1", page=1, per_page=10)
    assert total == 3
    assert len(result) == 3
    assert {e.id for e in result} == {"exec-1", "exec-2", "exec-3"}

    # Solo pipe-2
    result_p2, total_p2 = await execution_repository.find_by_pipeline_id("pipe-2", page=1, per_page=10)
    assert total_p2 == 1
    assert len(result_p2) == 1
    assert result_p2[0].id == "exec-4"

    # Paginación
    page1, total = await execution_repository.find_by_pipeline_id("pipe-1", page=1, per_page=2)
    assert total == 3
    assert len(page1) == 2
    page2, _ = await execution_repository.find_by_pipeline_id("pipe-1", page=2, per_page=2)
    assert len(page2) == 1
    assert {e.id for e in page1}.isdisjoint({e.id for e in page2})


# ---------------------------------------------------------------------------
# Test 4: find_latest_by_pipeline — devuelve la más reciente
# ---------------------------------------------------------------------------

async def test_find_latest_by_pipeline(execution_repository):
    """find_latest_by_pipeline devuelve la ejecución creada más recientemente."""
    import asyncio
    early = make_execution("exec-early", "pipe-1")
    await execution_repository.save(early)

    late = make_execution(
        "exec-late",
        "pipe-1",
        started_at=datetime(2026, 1, 2, 12, 0, 0),
    )
    # Ajustar created_at manualmente para garantizar orden
    late.created_at = datetime(2026, 1, 2, 12, 0, 0)
    await execution_repository.save(late)

    latest = await execution_repository.find_latest_by_pipeline("pipe-1")
    assert latest is not None
    assert latest.id == "exec-late"


async def test_find_latest_by_pipeline_no_executions(execution_repository):
    """find_latest_by_pipeline devuelve None si no hay ejecuciones."""
    result = await execution_repository.find_latest_by_pipeline("pipe-x")
    assert result is None
