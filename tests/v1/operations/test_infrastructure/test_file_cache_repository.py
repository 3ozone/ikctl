"""Tests de integración para SQLAlchemyFileCacheRepository (T-18)."""
from datetime import datetime

import pytest


# ---------------------------------------------------------------------------
# Test 1: find_hash — None cuando no existe entrada
# ---------------------------------------------------------------------------


async def test_find_hash_returns_none_when_not_found(file_cache_repository):
    """find_hash devuelve None si no existe entrada para (server_id, kit_id, filename)."""
    result = await file_cache_repository.find_hash("srv-1", "kit-1", "file.sh")
    assert result is None


# ---------------------------------------------------------------------------
# Test 2: upsert + find_hash — roundtrip INSERT
# ---------------------------------------------------------------------------


async def test_upsert_and_find_hash(file_cache_repository):
    """upsert persiste el hash y find_hash lo recupera correctamente."""
    await file_cache_repository.upsert("srv-1", "kit-1", "deploy.sh", "abc123")

    result = await file_cache_repository.find_hash("srv-1", "kit-1", "deploy.sh")
    assert result == "abc123"

    # Clave diferente → None
    assert await file_cache_repository.find_hash("srv-1", "kit-1", "other.sh") is None
    assert await file_cache_repository.find_hash("srv-2", "kit-1", "deploy.sh") is None


# ---------------------------------------------------------------------------
# Test 3: upsert idempotente — UPDATE al re-insertar misma clave
# ---------------------------------------------------------------------------


async def test_upsert_updates_existing_hash(file_cache_repository):
    """Llamar upsert dos veces con misma clave actualiza el hash (no duplica)."""
    await file_cache_repository.upsert("srv-1", "kit-1", "config.yaml", "hash-v1")
    await file_cache_repository.upsert("srv-1", "kit-1", "config.yaml", "hash-v2")

    result = await file_cache_repository.find_hash("srv-1", "kit-1", "config.yaml")
    assert result == "hash-v2"


# ---------------------------------------------------------------------------
# Test 4: invalidate_server_kit — elimina todas las entradas del par (server, kit)
# ---------------------------------------------------------------------------


async def test_invalidate_server_kit(file_cache_repository):
    """invalidate_server_kit borra todas las entradas de (server_id, kit_id)."""
    await file_cache_repository.upsert("srv-1", "kit-1", "a.sh", "hash-a")
    await file_cache_repository.upsert("srv-1", "kit-1", "b.sh", "hash-b")
    await file_cache_repository.upsert("srv-1", "kit-2", "a.sh", "hash-c")  # otro kit

    await file_cache_repository.invalidate_server_kit("srv-1", "kit-1")

    assert await file_cache_repository.find_hash("srv-1", "kit-1", "a.sh") is None
    assert await file_cache_repository.find_hash("srv-1", "kit-1", "b.sh") is None
    # El otro kit NO se ve afectado
    assert await file_cache_repository.find_hash("srv-1", "kit-2", "a.sh") == "hash-c"


# ---------------------------------------------------------------------------
# Test 5: invalidate_server_kit sin entradas — no falla (idempotente)
# ---------------------------------------------------------------------------


async def test_invalidate_server_kit_empty_is_idempotent(file_cache_repository):
    """invalidate_server_kit sobre entradas inexistentes no lanza excepción."""
    await file_cache_repository.invalidate_server_kit("srv-ghost", "kit-ghost")  # no debe lanzar
