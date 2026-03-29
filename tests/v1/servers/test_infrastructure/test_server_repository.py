"""Tests para SQLAlchemyServerRepository (T-32).

Verifica:
- Operaciones CRUD con DB real (SQLite in-memory)
- Scoping por user_id: un usuario no accede a servidores de otro
- find_local_by_user: filtra solo servidores de tipo local
- has_active_operations: retorna True/False según operaciones activas
"""
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.infrastructure.persistence.models import Base
from app.v1.servers.infrastructure.repositories.server_repository import (
    SQLAlchemyServerRepository,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_engine():
    """Crea engine SQLite in-memory para tests.

    Crea también la tabla `operations` mínima que necesita has_active_operations.
    Esta tabla pertenece al módulo operations (aún sin modelos SQLAlchemy propios).
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS operations ("
                "id TEXT PRIMARY KEY, "
                "server_id TEXT NOT NULL, "
                "user_id TEXT NOT NULL, "
                "type TEXT NOT NULL, "
                "status TEXT NOT NULL, "
                "created_at TEXT NOT NULL, "
                "updated_at TEXT NOT NULL"
                ")"
            )
        )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Sesión de base de datos para cada test."""
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def server_repository(db_session):
    """Fixture SQLAlchemyServerRepository con DB real."""
    return SQLAlchemyServerRepository(db_session)


def _make_remote_server(
    server_id: str = "srv-001",
    user_id: str = "user-001",
) -> Server:
    return Server(
        id=server_id,
        user_id=user_id,
        name="Production Server",
        type=ServerType("remote"),
        status=ServerStatus("active"),
        host="192.168.1.10",
        port=22,
        credential_id="cred-001",
        description="Main prod server",
        os_id=None,
        os_version=None,
        os_name=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_local_server(
    server_id: str = "srv-local",
    user_id: str = "user-001",
) -> Server:
    return Server(
        id=server_id,
        user_id=user_id,
        name="Local Server",
        type=ServerType("local"),
        status=ServerStatus("active"),
        host=None,
        port=None,
        credential_id=None,
        description=None,
        os_id=None,
        os_version=None,
        os_name=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_and_find_by_id(server_repository):
    """Test 1: save persiste el servidor y find_by_id lo recupera correctamente."""
    server = _make_remote_server()
    await server_repository.save(server)

    found = await server_repository.find_by_id("srv-001", "user-001")
    assert found is not None
    assert found.id == "srv-001"
    assert found.user_id == "user-001"
    assert found.name == "Production Server"
    assert found.type.value == "remote"
    assert found.status.value == "active"
    assert found.host == "192.168.1.10"
    assert found.port == 22
    assert found.credential_id == "cred-001"


@pytest.mark.asyncio
async def test_find_by_id_wrong_user_returns_none(server_repository):
    """Test 2: find_by_id retorna None si el servidor no pertenece al usuario."""
    await server_repository.save(_make_remote_server(user_id="user-001"))

    not_found = await server_repository.find_by_id("srv-001", "user-OTRO")
    assert not_found is None


@pytest.mark.asyncio
async def test_find_all_by_user_pagination(server_repository):
    """Test 3: find_all_by_user lista servidores del usuario con paginación y aislamiento."""
    for i in range(1, 5):
        srv = _make_remote_server(server_id=f"srv-{i:03d}", user_id="user-001")
        srv.name = f"Server {i}"
        await server_repository.save(srv)

    # Servidor de otro usuario
    await server_repository.save(_make_remote_server(server_id="srv-other", user_id="user-002"))

    page1 = await server_repository.find_all_by_user("user-001", page=1, per_page=2)
    assert len(page1) == 2

    page2 = await server_repository.find_all_by_user("user-001", page=2, per_page=2)
    assert len(page2) == 2

    all_ids = {s.id for s in page1 + page2}
    assert "srv-other" not in all_ids


@pytest.mark.asyncio
async def test_update_server(server_repository):
    """Test 4: update persiste los cambios del servidor."""
    server = _make_remote_server()
    await server_repository.save(server)

    server.name = "Updated Server"
    server.host = "10.0.0.1"
    await server_repository.update(server)

    found = await server_repository.find_by_id("srv-001", "user-001")
    assert found is not None
    assert found.name == "Updated Server"
    assert found.host == "10.0.0.1"


@pytest.mark.asyncio
async def test_delete_server(server_repository):
    """Test 5: delete elimina el servidor de la base de datos."""
    await server_repository.save(_make_remote_server())

    await server_repository.delete("srv-001")

    found = await server_repository.find_by_id("srv-001", "user-001")
    assert found is None


@pytest.mark.asyncio
async def test_find_local_by_user(server_repository):
    """Test 6: find_local_by_user retorna solo servidores de tipo local del usuario."""
    await server_repository.save(_make_remote_server(server_id="srv-remote", user_id="user-001"))
    await server_repository.save(_make_local_server(server_id="srv-local", user_id="user-001"))
    # Local de otro usuario — no debe aparecer
    await server_repository.save(_make_local_server(server_id="srv-local-2", user_id="user-002"))

    locals_ = await server_repository.find_local_by_user("user-001")
    assert len(locals_) == 1
    assert locals_[0].id == "srv-local"
    assert locals_[0].type.value == "local"


@pytest.mark.asyncio
async def test_has_active_operations(server_repository, db_session):
    """Test 7: has_active_operations retorna True si hay ops activas, False si no."""
    await server_repository.save(_make_remote_server())

    # Sin operaciones: debe retornar False
    assert await server_repository.has_active_operations("srv-001") is False

    # Insertar una operación activa (status pending) directamente en BD
    await db_session.execute(
        text(
            "INSERT INTO operations "
            "(id, server_id, user_id, type, status, created_at, updated_at) "
            "VALUES ('op-001', 'srv-001', 'user-001', 'install', 'pending', "
            "datetime('now'), datetime('now'))"
        )
    )
    await db_session.commit()

    assert await server_repository.has_active_operations("srv-001") is True
