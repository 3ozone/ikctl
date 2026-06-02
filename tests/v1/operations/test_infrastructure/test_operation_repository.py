"""Tests de integración para SQLAlchemyOperationRepository (T-17)."""
from datetime import datetime

import pytest

from app.v1.operations.domain.entities.operation import Operation
from app.v1.operations.domain.value_objects.operation_status import OperationStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_operation(
    op_id: str,
    user_id: str = "user-1",
    server_id: str = "server-1",
    kit_id: str = "kit-1",
    status: str = "pending",
    output: str = "",
    backup_files: tuple = (),
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> Operation:
    now = datetime(2024, 1, 1, 12, 0, 0)
    return Operation(
        id=op_id,
        user_id=user_id,
        server_id=server_id,
        kit_id=kit_id,
        values={},
        sudo=False,
        status=OperationStatus(status),
        debug_level="none",
        output=output,
        backup_files=backup_files,
        created_at=now,
        updated_at=now,
        started_at=started_at,
        finished_at=finished_at,
    )


# ---------------------------------------------------------------------------
# Test 1: save y find_by_id — roundtrip completo
# ---------------------------------------------------------------------------


async def test_save_and_find_by_id(operation_repository):
    """save persiste la operación y find_by_id la recupera con todos sus campos."""
    op = _make_operation("op-1", backup_files=("/tmp/backup.tar.gz",))
    await operation_repository.save(op)

    found = await operation_repository.find_by_id("op-1", "user-1")

    assert found is not None
    assert found.id == "op-1"
    assert found.user_id == "user-1"
    assert found.server_id == "server-1"
    assert found.kit_id == "kit-1"
    assert found.status == OperationStatus("pending")
    assert found.debug_level == "none"
    assert found.output == ""
    assert found.backup_files == ("/tmp/backup.tar.gz",)  # roundtrip tuple ↔ JSON

    # usuario incorrecto → None
    assert await operation_repository.find_by_id("op-1", "other-user") is None

    # id inexistente → None
    assert await operation_repository.find_by_id("does-not-exist", "user-1") is None


# ---------------------------------------------------------------------------
# Test 2: find_by_id_no_ownership — ignora el user_id
# ---------------------------------------------------------------------------


async def test_find_by_id_no_ownership(operation_repository):
    """find_by_id_no_ownership devuelve la op sin validar user_id (uso interno tasks)."""
    op = _make_operation("op-2", user_id="user-2")
    await operation_repository.save(op)

    # Otro user_id → aun así lo encuentra
    found = await operation_repository.find_by_id_no_ownership("op-2")
    assert found is not None
    assert found.id == "op-2"
    assert found.user_id == "user-2"

    # ID inexistente → None
    assert await operation_repository.find_by_id_no_ownership("nope") is None


# ---------------------------------------------------------------------------
# Test 3: update — persiste cambios de estado, output y backup_files
# ---------------------------------------------------------------------------


async def test_update_persists_state_changes(operation_repository):
    """update persiste status, output, backup_files, started_at, finished_at."""
    op = _make_operation("op-3")
    await operation_repository.save(op)

    started = datetime(2024, 1, 1, 12, 5, 0)
    finished = datetime(2024, 1, 1, 12, 10, 0)
    op.start(started)
    op.append_output("line1\n")
    op.complete(finished)
    op.backup_files = ("/tmp/a.tar.gz", "/tmp/b.tar.gz")
    await operation_repository.update(op)

    refreshed = await operation_repository.find_by_id("op-3", "user-1")
    assert refreshed is not None
    assert refreshed.status == OperationStatus("completed")
    assert refreshed.output == "line1\n"
    assert refreshed.backup_files == ("/tmp/a.tar.gz", "/tmp/b.tar.gz")
    assert refreshed.started_at == started
    assert refreshed.finished_at == finished


# ---------------------------------------------------------------------------
# Test 4: find_all_by_user — paginación y filtros server_id, kit_id, status
# ---------------------------------------------------------------------------


async def test_find_all_by_user_filters_and_pagination(operation_repository):
    """find_all_by_user respeta paginación y filtros opcionales."""
    await operation_repository.save(_make_operation("op-a", server_id="srv-1", kit_id="kit-1", status="pending"))
    await operation_repository.save(_make_operation("op-b", server_id="srv-1", kit_id="kit-2", status="completed"))
    await operation_repository.save(_make_operation("op-c", server_id="srv-2", kit_id="kit-1", status="pending"))
    await operation_repository.save(_make_operation("op-d", user_id="user-2", server_id="srv-1", kit_id="kit-1", status="pending"))

    # Sin filtros: las 3 operaciones del user-1
    ops, total = await operation_repository.find_all_by_user("user-1", page=1, per_page=10)
    assert total == 3
    assert len(ops) == 3
    assert {o.id for o in ops} == {"op-a", "op-b", "op-c"}

    # Filtro server_id
    ops, total = await operation_repository.find_all_by_user("user-1", page=1, per_page=10, server_id="srv-1")
    assert total == 2
    assert {o.id for o in ops} == {"op-a", "op-b"}

    # Filtro kit_id
    ops, total = await operation_repository.find_all_by_user("user-1", page=1, per_page=10, kit_id="kit-1")
    assert total == 2
    assert {o.id for o in ops} == {"op-a", "op-c"}

    # Filtro status
    ops, total = await operation_repository.find_all_by_user("user-1", page=1, per_page=10, status="pending")
    assert total == 2
    assert {o.id for o in ops} == {"op-a", "op-c"}

    # Paginación: page=1 per_page=2
    ops, total = await operation_repository.find_all_by_user("user-1", page=1, per_page=2)
    assert total == 3
    assert len(ops) == 2

    # Paginación: page=2 per_page=2
    ops_p2, _ = await operation_repository.find_all_by_user("user-1", page=2, per_page=2)
    assert len(ops_p2) == 1
    assert {o.id for o in ops}.isdisjoint({o.id for o in ops_p2})


# ---------------------------------------------------------------------------
# Test 5: update de operación inexistente — no falla (idempotente)
# ---------------------------------------------------------------------------


async def test_update_nonexistent_does_not_raise(operation_repository):
    """update sobre operación inexistente no lanza excepción."""
    op = _make_operation("op-ghost")
    await operation_repository.update(op)  # no debe lanzar


# ---------------------------------------------------------------------------
# Test 6: backup_files vacío — roundtrip tuple vacía
# ---------------------------------------------------------------------------


async def test_empty_backup_files_roundtrip(operation_repository):
    """backup_files vacío se persiste y recupera como tupla vacía."""
    op = _make_operation("op-nobak", backup_files=())
    await operation_repository.save(op)

    found = await operation_repository.find_by_id("op-nobak", "user-1")
    assert found is not None
    assert found.backup_files == ()
    assert isinstance(found.backup_files, tuple)
