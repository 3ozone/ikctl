"""Tests para PasswordHistoryRepository."""
import asyncio
from datetime import datetime, timezone, timedelta
import pytest

from app.v1.auth.domain.entities import PasswordHistory


@pytest.mark.asyncio
async def test_save_password_history_success(password_history_repository):
    """Test 1: Guarda una entrada de historial exitosamente."""
    user_id = "user-456"
    password_hash = "$2b$12$hashed_password_example"

    await password_history_repository.save(user_id, password_hash)

    # Verificar que se guardó recuperando el historial
    history = await password_history_repository.find_last_n_by_user(user_id, 1)

    assert len(history) == 1
    assert history[0].user_id == user_id
    assert history[0].password_hash == password_hash


@pytest.mark.asyncio
async def test_find_last_n_returns_correct_count(password_history_repository):
    """Test 2: find_last_n_by_user retorna el número correcto de entradas."""
    user_id = "user-789"

    # Guardar 5 contraseñas con pequeña diferencia de tiempo
    for i in range(5):
        await password_history_repository.save(user_id, f"hash_{i}")
        # Pequeño delay para asegurar orden de created_at
        await asyncio.sleep(0.01)

    # Obtener últimas 3
    history = await password_history_repository.find_last_n_by_user(user_id, 3)

    assert len(history) == 3


@pytest.mark.asyncio
async def test_find_last_n_returns_in_descending_order(password_history_repository):
    """Test 3: find_last_n_by_user retorna en orden descendente (más reciente primero)."""
    user_id = "user-order-test"

    # Guardar 3 contraseñas con orden conocido
    hashes = ["hash_1_oldest", "hash_2_middle", "hash_3_newest"]
    for hash_value in hashes:
        await password_history_repository.save(user_id, hash_value)
        await asyncio.sleep(0.01)

    # Obtener últimas 3
    history = await password_history_repository.find_last_n_by_user(user_id, 3)

    # Verificar orden descendente (más reciente primero)
    assert history[0].password_hash == "hash_3_newest"
    assert history[1].password_hash == "hash_2_middle"
    assert history[2].password_hash == "hash_1_oldest"


@pytest.mark.asyncio
async def test_find_last_n_with_fewer_entries(password_history_repository):
    """Test 4: find_last_n_by_user con menos entradas que N solicitadas."""
    user_id = "user-few-entries"

    # Guardar solo 2 contraseñas
    await password_history_repository.save(user_id, "hash_1")
    await password_history_repository.save(user_id, "hash_2")

    # Solicitar últimas 5 (pero solo hay 2)
    history = await password_history_repository.find_last_n_by_user(user_id, 5)

    assert len(history) == 2


@pytest.mark.asyncio
async def test_find_last_n_empty_for_nonexistent_user(password_history_repository):
    """Test 5: find_last_n_by_user retorna lista vacía para usuario sin historial."""
    history = await password_history_repository.find_last_n_by_user("nonexistent-user", 3)

    assert history == []


@pytest.mark.asyncio
async def test_multiple_users_independent_history(password_history_repository):
    """Test 6: Múltiples usuarios tienen historiales independientes."""
    user_1 = "user-1"
    user_2 = "user-2"

    # Usuario 1: 3 contraseñas
    for i in range(3):
        await password_history_repository.save(user_1, f"user1_hash_{i}")

    # Usuario 2: 2 contraseñas
    for i in range(2):
        await password_history_repository.save(user_2, f"user2_hash_{i}")

    # Verificar historiales independientes
    history_1 = await password_history_repository.find_last_n_by_user(user_1, 10)
    history_2 = await password_history_repository.find_last_n_by_user(user_2, 10)

    assert len(history_1) == 3
    assert len(history_2) == 2
    assert all("user1_hash" in h.password_hash for h in history_1)
    assert all("user2_hash" in h.password_hash for h in history_2)


@pytest.mark.asyncio
async def test_save_multiple_same_user_accumulates(password_history_repository):
    """Test 7: Guardar múltiples entradas para mismo usuario acumula historial."""
    user_id = "user-accumulate"

    await password_history_repository.save(user_id, "hash_old")
    await password_history_repository.save(user_id, "hash_new")

    history = await password_history_repository.find_last_n_by_user(user_id, 10)

    # Ambas entradas deben estar presentes
    assert len(history) == 2
