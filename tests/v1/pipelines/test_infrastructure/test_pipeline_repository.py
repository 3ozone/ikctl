"""Tests de integración para SQLAlchemyPipelineRepository — T-19."""
from datetime import datetime, timezone

import pytest

from app.v1.pipelines.domain.entities.pipeline import Pipeline
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_pipeline(
    pipeline_id: str = "pipe-1",
    user_id: str = "user-1",
    name: str = "Mi Pipeline",
    targets: list | None = None,
    kits: list | None = None,
    values: dict | None = None,
    sudo: bool = False,
    debug_level: str = "none",
    description: str | None = None,
) -> Pipeline:
    return Pipeline(
        id=pipeline_id,
        user_id=user_id,
        name=name,
        description=description,
        targets=targets or [PipelineTarget(server_id="srv-1")],
        kits=kits or [PipelineKitConfig(kit_id="kit-1")],
        values=values or {},
        sudo=sudo,
        debug_level=debug_level,
        created_at=NOW,
        updated_at=NOW,
    )


# ---------------------------------------------------------------------------
# Test 1: save y find_by_id — roundtrip completo
# ---------------------------------------------------------------------------

async def test_save_and_find_by_id(pipeline_repository):
    """save persiste el pipeline y find_by_id lo recupera con todos sus campos."""
    pipeline = make_pipeline(
        targets=[PipelineTarget(server_id="srv-1"), PipelineTarget(server_id="srv-2")],
        kits=[PipelineKitConfig(kit_id="kit-1", sudo=True), PipelineKitConfig(kit_id="kit-2")],
        values={"key": "val"},
        sudo=True,
        debug_level="errors",
        description="desc test",
    )
    await pipeline_repository.save(pipeline)

    found = await pipeline_repository.find_by_id("pipe-1", "user-1")

    assert found is not None
    assert found.id == "pipe-1"
    assert found.user_id == "user-1"
    assert found.name == "Mi Pipeline"
    assert found.description == "desc test"
    assert found.sudo is True
    assert found.debug_level == "errors"
    assert found.values == {"key": "val"}
    # Roundtrip targets
    assert len(found.targets) == 2
    assert found.targets[0].server_id == "srv-1"
    assert found.targets[1].server_id == "srv-2"
    # Roundtrip kits
    assert len(found.kits) == 2
    assert found.kits[0].kit_id == "kit-1"
    assert found.kits[0].sudo is True
    assert found.kits[1].kit_id == "kit-2"
    assert found.kits[1].sudo is None


async def test_save_and_find_kit_values_roundtrip(pipeline_repository):
    """save persiste los values por kit y find_by_id los recupera correctamente."""
    pipeline = make_pipeline(
        kits=[
            PipelineKitConfig(kit_id="kit-1", values={"command": "hostname"}),
            PipelineKitConfig(kit_id="kit-2", values={}),
        ],
    )
    await pipeline_repository.save(pipeline)

    found = await pipeline_repository.find_by_id("pipe-1", "user-1")

    assert found is not None
    assert found.kits[0].values == {"command": "hostname"}
    assert found.kits[1].values == {}


async def test_find_by_id_wrong_user_returns_none(pipeline_repository):
    """find_by_id con user_id incorrecto devuelve None (ownership)."""
    await pipeline_repository.save(make_pipeline())

    assert await pipeline_repository.find_by_id("pipe-1", "other-user") is None


async def test_find_by_id_nonexistent_returns_none(pipeline_repository):
    """find_by_id con id inexistente devuelve None."""
    assert await pipeline_repository.find_by_id("does-not-exist", "user-1") is None


# ---------------------------------------------------------------------------
# Test 2: find_by_id_no_ownership — ignora user_id
# ---------------------------------------------------------------------------

async def test_find_by_id_no_ownership(pipeline_repository):
    """find_by_id_no_ownership devuelve el pipeline sin validar user_id."""
    await pipeline_repository.save(make_pipeline(user_id="user-2"))

    found = await pipeline_repository.find_by_id_no_ownership("pipe-1")
    assert found is not None
    assert found.user_id == "user-2"

    assert await pipeline_repository.find_by_id_no_ownership("nope") is None


# ---------------------------------------------------------------------------
# Test 3: update — persiste cambios de nombre, targets, kits, values, sudo
# ---------------------------------------------------------------------------

async def test_update_persists_changes(pipeline_repository):
    """update persiste todos los campos mutables del pipeline."""
    pipeline = make_pipeline()
    await pipeline_repository.save(pipeline)

    pipeline.update(
        name="Nuevo Nombre",
        description="nueva desc",
        targets=[PipelineTarget(server_id="srv-99")],
        kits=[PipelineKitConfig(kit_id="kit-99", debug_level="full")],
        values={"x": 1},
        sudo=True,
        debug_level="full",
    )
    await pipeline_repository.update(pipeline)

    refreshed = await pipeline_repository.find_by_id("pipe-1", "user-1")
    assert refreshed is not None
    assert refreshed.name == "Nuevo Nombre"
    assert refreshed.description == "nueva desc"
    assert refreshed.sudo is True
    assert refreshed.debug_level == "full"
    assert refreshed.values == {"x": 1}
    assert len(refreshed.targets) == 1
    assert refreshed.targets[0].server_id == "srv-99"
    assert refreshed.kits[0].kit_id == "kit-99"
    assert refreshed.kits[0].debug_level == "full"


# ---------------------------------------------------------------------------
# Test 4: delete — elimina el pipeline
# ---------------------------------------------------------------------------

async def test_delete_removes_pipeline(pipeline_repository):
    """delete elimina el pipeline; find_by_id devuelve None después."""
    await pipeline_repository.save(make_pipeline())

    await pipeline_repository.delete("pipe-1")

    assert await pipeline_repository.find_by_id("pipe-1", "user-1") is None


# ---------------------------------------------------------------------------
# Test 5: find_all_by_user — paginación y scoping por usuario
# ---------------------------------------------------------------------------

async def test_find_all_by_user_pagination_and_scoping(pipeline_repository):
    """find_all_by_user devuelve solo los pipelines del usuario, paginados."""
    await pipeline_repository.save(make_pipeline("pipe-1", "user-1", "P1"))
    await pipeline_repository.save(make_pipeline("pipe-2", "user-1", "P2"))
    await pipeline_repository.save(make_pipeline("pipe-3", "user-1", "P3"))
    await pipeline_repository.save(make_pipeline("pipe-4", "user-2", "P4"))

    # Todos los del user-1
    result, total = await pipeline_repository.find_all_by_user("user-1", page=1, per_page=10)
    assert total == 3
    assert len(result) == 3
    assert {p.id for p in result} == {"pipe-1", "pipe-2", "pipe-3"}

    # Paginación: page 1, per_page 2
    page1, total = await pipeline_repository.find_all_by_user("user-1", page=1, per_page=2)
    assert total == 3
    assert len(page1) == 2

    # Paginación: page 2, per_page 2
    page2, _ = await pipeline_repository.find_all_by_user("user-1", page=2, per_page=2)
    assert len(page2) == 1
    assert {p.id for p in page1}.isdisjoint({p.id for p in page2})

    # user-2 solo ve el suyo
    result_u2, total_u2 = await pipeline_repository.find_all_by_user("user-2", page=1, per_page=10)
    assert total_u2 == 1
    assert len(result_u2) == 1
    assert result_u2[0].id == "pipe-4"


# ---------------------------------------------------------------------------
# Test 6: has_active_executions — requiere tabla pipeline_executions
# ---------------------------------------------------------------------------

async def test_has_active_executions_returns_false_when_no_executions(pipeline_repository):
    """has_active_executions devuelve False si no hay ejecuciones activas."""
    await pipeline_repository.save(make_pipeline())

    result = await pipeline_repository.has_active_executions("pipe-1")
    assert result is False
