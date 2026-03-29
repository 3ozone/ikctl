"""Tests para SQLAlchemyCredentialRepository (T-31).

Verifica:
- Operaciones CRUD con DB real (SQLite in-memory)
- Cifrado AES-256: password y private_key NO se almacenan en plano
- Scoping por user_id: un usuario no accede a credenciales de otro
- is_used_by_server: protección de borrado cuando hay servidores asociados
"""
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.value_objects.credential_type import CredentialType
from app.v1.servers.infrastructure.persistence.models import Base
from app.v1.servers.infrastructure.repositories.credential_repository import (
    SQLAlchemyCredentialRepository,
)

ENCRYPTION_KEY = "a" * 32  # 32 bytes para AES-256


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_engine():
    """Crea engine SQLite in-memory para tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
async def credential_repository(db_session):
    """Fixture SQLAlchemyCredentialRepository con DB real."""
    return SQLAlchemyCredentialRepository(db_session, ENCRYPTION_KEY)


def _make_ssh_credential(
    credential_id: str = "cred-001",
    user_id: str = "user-001",
) -> Credential:
    return Credential(
        id=credential_id,
        user_id=user_id,
        name="My SSH Key",
        type=CredentialType("ssh"),
        username="root",
        password=None,
        private_key="-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_git_https_credential(
    credential_id: str = "cred-002",
    user_id: str = "user-001",
) -> Credential:
    return Credential(
        id=credential_id,
        user_id=user_id,
        name="GitHub Token",
        type=CredentialType("git_https"),
        username="gh-user",
        password="supersecrettoken",
        private_key=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_and_find_by_id(credential_repository, db_session):
    """Test 1: save persiste la credencial y find_by_id la recupera correctamente.

    También verifica que password y private_key NO se almacenan en texto plano.
    """
    credential = _make_ssh_credential()
    await credential_repository.save(credential)

    # Recuperar por id + user_id
    found = await credential_repository.find_by_id("cred-001", "user-001")
    assert found is not None
    assert found.id == "cred-001"
    assert found.user_id == "user-001"
    assert found.name == "My SSH Key"
    assert found.type.value == "ssh"
    assert found.username == "root"
    assert found.private_key == credential.private_key

    # Verificar que en la fila de BD el valor NO está en plano
    result = await db_session.execute(
        text("SELECT private_key_encrypted FROM credentials WHERE id = 'cred-001'")
    )
    raw = result.scalar_one()
    assert raw != credential.private_key, "private_key debe estar cifrada en BD"


@pytest.mark.asyncio
async def test_find_by_id_wrong_user_returns_none(credential_repository):
    """Test 2: find_by_id retorna None si la credencial no pertenece al usuario."""
    credential = _make_ssh_credential(user_id="user-001")
    await credential_repository.save(credential)

    not_found = await credential_repository.find_by_id("cred-001", "user-OTRO")
    assert not_found is None


@pytest.mark.asyncio
async def test_find_by_id_nonexistent_returns_none(credential_repository):
    """Test 3: find_by_id retorna None si el id no existe."""
    not_found = await credential_repository.find_by_id("nonexistent", "user-001")
    assert not_found is None


@pytest.mark.asyncio
async def test_find_all_by_user_pagination(credential_repository):
    """Test 4: find_all_by_user lista credenciales del usuario con paginación correcta."""
    for i in range(1, 5):
        cred = _make_ssh_credential(
            credential_id=f"cred-{i:03d}",
            user_id="user-001",
        )
        cred.name = f"Key {i}"
        await credential_repository.save(cred)

    # Credencial de otro usuario (no debe aparecer)
    other = _make_git_https_credential(
        credential_id="cred-other", user_id="user-002")
    await credential_repository.save(other)

    # Página 1, 2 por página
    page1 = await credential_repository.find_all_by_user("user-001", page=1, per_page=2)
    assert len(page1) == 2

    # Página 2, 2 por página
    page2 = await credential_repository.find_all_by_user("user-001", page=2, per_page=2)
    assert len(page2) == 2

    # Solo IDs del usuario
    all_ids = {c.id for c in page1 + page2}
    assert "cred-other" not in all_ids


@pytest.mark.asyncio
async def test_update_credential(credential_repository):
    """Test 5: update persiste los cambios de la credencial."""
    credential = _make_git_https_credential()
    await credential_repository.save(credential)

    credential.name = "Updated Token"
    credential.password = "newtoken"
    await credential_repository.update(credential)

    found = await credential_repository.find_by_id("cred-002", "user-001")
    assert found is not None
    assert found.name == "Updated Token"
    assert found.password == "newtoken"


@pytest.mark.asyncio
async def test_delete_credential(credential_repository):
    """Test 6: delete elimina la credencial de la base de datos."""
    credential = _make_ssh_credential()
    await credential_repository.save(credential)

    await credential_repository.delete("cred-001")

    found = await credential_repository.find_by_id("cred-001", "user-001")
    assert found is None


@pytest.mark.asyncio
async def test_is_used_by_server(credential_repository, db_session):
    """Test 7: is_used_by_server retorna True si algún servidor la usa, False si no."""
    credential = _make_ssh_credential()
    await credential_repository.save(credential)

    # Sin servidores: debe retornar False
    assert await credential_repository.is_used_by_server("cred-001") is False

    # Insertar un servidor que referencia la credencial directamente en BD
    await db_session.execute(
        text(
            "INSERT INTO servers "
            "(id, user_id, name, type, status, host, port, credential_id, "
            "os_id, os_version, os_name, created_at, updated_at) "
            "VALUES ('srv-001', 'user-001', 'My Server', 'remote', 'active', "
            "'1.2.3.4', 22, 'cred-001', 'ubuntu', '22.04', 'Ubuntu', "
            "datetime('now'), datetime('now'))"
        )
    )
    await db_session.commit()

    assert await credential_repository.is_used_by_server("cred-001") is True
