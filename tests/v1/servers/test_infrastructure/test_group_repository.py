"""Tests para SQLAlchemyGroupRepository (T-33).

Verifica:
- Operaciones CRUD con DB real (SQLite in-memory)
- Persistencia de server_ids a través de la tabla group_members
- Scoping por user_id: un usuario no accede a grupos de otro
- has_active_pipeline_executions: retorna True/False según ejecuciones activas
  (busca group_id en JSON targets de pipelines y luego ejecuciones activas)
"""
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.v1.servers.domain.entities.group import Group
from app.v1.servers.infrastructure.persistence.models import Base
from app.v1.servers.infrastructure.repositories.group_repository import (
    SQLAlchemyGroupRepository,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_engine():
    """Crea engine SQLite in-memory para tests.

    Crea también las tablas `pipelines` y `pipeline_executions` que necesita
    has_active_pipeline_executions (busca group_id en JSON targets).
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS pipelines ("
                "id TEXT PRIMARY KEY, "
                "user_id TEXT NOT NULL, "
                "name TEXT NOT NULL, "
                "description TEXT, "
                "targets TEXT NOT NULL DEFAULT '[]', "
                "kits TEXT NOT NULL DEFAULT '[]', "
                "pipeline_values TEXT NOT NULL DEFAULT '{}', "
                "sudo INTEGER NOT NULL DEFAULT 0, "
                "debug_level TEXT NOT NULL DEFAULT 'none', "
                "created_at TEXT NOT NULL, "
                "updated_at TEXT NOT NULL"
                ")"
            )
        )
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS pipeline_executions ("
                "id TEXT PRIMARY KEY, "
                "pipeline_id TEXT NOT NULL, "
                "user_id TEXT NOT NULL, "
                "status TEXT NOT NULL, "
                "operation_ids TEXT NOT NULL DEFAULT '[]', "
                "snapshot TEXT NOT NULL DEFAULT '{}', "
                "started_at TEXT, "
                "finished_at TEXT, "
                "created_at TEXT NOT NULL"
                ")"
            )
        )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Sesión de base de datos para cada test."""
    factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def group_repository(db_session):
    """Fixture SQLAlchemyGroupRepository con DB real."""
    return SQLAlchemyGroupRepository(db_session)


def _make_group(
    group_id: str = "grp-001",
    user_id: str = "user-001",
    server_ids: list[str] | None = None,
) -> Group:
    return Group(
        id=group_id,
        user_id=user_id,
        name="Production Group",
        description="Servidores de producción",
        server_ids=server_ids or ["srv-001", "srv-002"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_and_find_by_id(group_repository):
    """Test 1: save persiste el grupo y find_by_id lo recupera con sus server_ids."""
    group = _make_group(server_ids=["srv-001", "srv-002"])
    await group_repository.save(group)

    found = await group_repository.find_by_id("grp-001", "user-001")
    assert found is not None
    assert found.id == "grp-001"
    assert found.user_id == "user-001"
    assert found.name == "Production Group"
    assert found.description == "Servidores de producción"
    assert set(found.server_ids) == {"srv-001", "srv-002"}


@pytest.mark.asyncio
async def test_find_by_id_wrong_user_returns_none(group_repository):
    """Test 2: find_by_id retorna None si el grupo no pertenece al usuario."""
    await group_repository.save(_make_group(user_id="user-001"))

    not_found = await group_repository.find_by_id("grp-001", "user-OTRO")
    assert not_found is None


@pytest.mark.asyncio
async def test_find_all_by_user_pagination(group_repository):
    """Test 3: find_all_by_user lista grupos del usuario con paginación y aislamiento."""
    for i in range(1, 5):
        grp = _make_group(group_id=f"grp-{i:03d}", user_id="user-001")
        grp.name = f"Group {i}"
        await group_repository.save(grp)

    # Grupo de otro usuario
    await group_repository.save(_make_group(group_id="grp-other", user_id="user-002"))

    page1 = await group_repository.find_all_by_user("user-001", page=1, per_page=2)
    assert len(page1) == 2

    page2 = await group_repository.find_all_by_user("user-001", page=2, per_page=2)
    assert len(page2) == 2

    all_ids = {g.id for g in page1 + page2}
    assert "grp-other" not in all_ids


@pytest.mark.asyncio
async def test_update_group(group_repository):
    """Test 4: update persiste los cambios del grupo incluyendo server_ids."""
    group = _make_group(server_ids=["srv-001", "srv-002"])
    await group_repository.save(group)

    group.name = "Updated Group"
    group.server_ids = ["srv-003"]
    await group_repository.update(group)

    found = await group_repository.find_by_id("grp-001", "user-001")
    assert found is not None
    assert found.name == "Updated Group"
    assert found.server_ids == ["srv-003"]


@pytest.mark.asyncio
async def test_delete_group(group_repository):
    """Test 5: delete elimina el grupo y sus group_members de la base de datos."""
    await group_repository.save(_make_group())

    await group_repository.delete("grp-001")

    found = await group_repository.find_by_id("grp-001", "user-001")
    assert found is None


@pytest.mark.asyncio
async def test_has_active_pipeline_executions(group_repository, db_session):
    """Test 6: has_active_pipeline_executions retorna True/False según ejecuciones activas.

    Un grupo se considera en uso si aparece en el JSON targets de un pipeline
    que tiene ejecuciones activas (pending/running).
    """
    await group_repository.save(_make_group())

    # Sin pipelines: debe retornar False
    assert await group_repository.has_active_pipeline_executions("grp-001") is False

    # Insertar un pipeline cuyo targets JSON contiene el group_id
    import json
    targets_json = json.dumps([{"server_id": "grp-001"}])
    kits_json = json.dumps([{"kit_id": "kit-001", "sudo": None, "debug_level": None}])
    await db_session.execute(
        text(
            "INSERT INTO pipelines "
            "(id, user_id, name, description, targets, kits, pipeline_values, sudo, debug_level, created_at, updated_at) "
            "VALUES ('pipe-001', 'user-001', 'Test Pipeline', 'desc', "
            ":targets, :kits, '{}', 0, 'none', "
            "datetime('now'), datetime('now'))"
        ),
        {"targets": targets_json, "kits": kits_json},
    )

    # Pipeline sin ejecuciones: debe retornar False
    await db_session.commit()
    assert await group_repository.has_active_pipeline_executions("grp-001") is False

    # Insertar una ejecución activa vinculada al pipeline
    await db_session.execute(
        text(
            "INSERT INTO pipeline_executions "
            "(id, pipeline_id, user_id, status, created_at) "
            "VALUES ('exec-001', 'pipe-001', 'user-001', 'running', "
            "datetime('now'))"
        )
    )
    await db_session.commit()

    # Pipeline con ejecución activa: debe retornar True
    assert await group_repository.has_active_pipeline_executions("grp-001") is True
