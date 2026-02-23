"""Tests para UserRepository."""
from datetime import datetime, timezone
import pytest

from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email


@pytest.mark.asyncio
async def test_save_user_success(user_repository):
    """Test 1: UserRepository guarda un usuario exitosamente."""
    user = User(
        id="user-123",
        name="John Doe",
        email=Email("john@example.com"),
        password_hash="hashed_password",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # Guardamos el usuario
    saved_user = await user_repository.save(user)

    # Verificamos que se guardó
    assert saved_user.id == user.id
    assert saved_user.name == user.name
    assert saved_user.email.value == user.email.value


@pytest.mark.asyncio
async def test_find_by_id_not_found(user_repository):
    """Test 2: UserRepository retorna None si el usuario no existe."""
    # Intentamos obtener un usuario que no existe
    found_user = await user_repository.find_by_id("non-existent-id")
    assert found_user is None


@pytest.mark.asyncio
async def test_find_by_email_success(user_repository):
    """Test 3: UserRepository obtiene un usuario por email."""
    user = User(
        id="user-456",
        name="Jane Doe",
        email=Email("jane@example.com"),
        password_hash="hashed_password",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # Guardamos el usuario
    await user_repository.save(user)

    # Obtenemos por email
    found_user = await user_repository.find_by_email("jane@example.com")

    # Verificamos que se encontró
    assert found_user is not None
    assert found_user.id == user.id
    assert found_user.email.value == "jane@example.com"

    # Email inexistente retorna None
    not_found = await user_repository.find_by_email("nonexistent@example.com")
    assert not_found is None


@pytest.mark.asyncio
async def test_update_user_success(user_repository):
    """Test 4: UserRepository actualiza un usuario existente."""
    user = User(
        id="user-789",
        name="Old Name",
        email=Email("update@example.com"),
        password_hash="hashed_password",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # Guardamos el usuario
    await user_repository.save(user)

    # Actualizamos el nombre
    user.name = "New Name"
    updated_user = await user_repository.update(user)

    # Verificamos la actualización
    assert updated_user.name == "New Name"

    # Verificamos consultando de nuevo
    found_user = await user_repository.find_by_id("user-789")
    assert found_user.name == "New Name"


@pytest.mark.asyncio
async def test_delete_user_success(user_repository):
    """Test 5: UserRepository elimina un usuario."""
    user = User(
        id="user-delete",
        name="Delete Me",
        email=Email("delete@example.com"),
        password_hash="hashed_password",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # Guardamos el usuario
    await user_repository.save(user)

    # Eliminamos
    await user_repository.delete("user-delete")

    # Verificamos que ya no existe
    found_user = await user_repository.find_by_id("user-delete")
    assert found_user is None
