"""Tests de integración FastAPI — flujos completos con DB real (T-55).

A diferencia de los tests de presentación con fakes, estos tests usan
repositorios SQLAlchemy reales sobre SQLite in-memory (StaticPool) para
validar que la capa HTTP, los use cases y la persistencia funcionan integrados.

StaticPool reutiliza la misma conexión → la DB in-memory persiste entre requests
dentro del mismo test, permitiendo flujos multi-step (register → login, etc.).

Flujos cubiertos:
    1. POST /register → usuario persiste realmente en DB → devuelve user_id
    2. POST /register → POST /login → flujo completo register + auth
    3. POST /register (x2 mismo email) → segundo intento retorna 409
    4. POST /login con email inexistente → 401
    5. POST /login con contraseña incorrecta → 401
"""
import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.v1.auth.infrastructure.persistence.models import Base
from app.v1.auth.infrastructure.presentation.deps import (
    get_db_session,
    get_event_bus,
    get_jwt_provider,
    get_login_attempt_tracker,
)
from main import app
from tests.v1.auth.test_presentation.conftest import (
    FakeEventBus,
    FakeJWTProvider,
    FakeLoginAttemptTracker,
)

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(name="integration_client")
def fixture_integration_client():
    """Cliente con DB SQLite in-memory real compartida entre requests via StaticPool.

    StaticPool garantiza que todos los requests del mismo test usan la misma
    conexión y por tanto ven la misma DB in-memory. Se overridea get_db_session
    para que todos los repos scoped reciban sesiones de esta DB de test.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def _create_schema():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_create_schema())

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db_session():
        async with session_factory() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_event_bus] = FakeEventBus
    app.dependency_overrides[get_jwt_provider] = FakeJWTProvider
    app.dependency_overrides[get_login_attempt_tracker] = FakeLoginAttemptTracker

    yield TestClient(app)

    app.dependency_overrides.clear()
    asyncio.get_event_loop().run_until_complete(engine.dispose())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_register_persists_user_and_returns_user_id(integration_client: TestClient):
    """Flujo 1: POST /register guarda el usuario en DB y devuelve user_id."""
    response = integration_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Integration User",
            "email": "integration@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "user_id" in data
    assert data["user_id"] is not None
    assert data["user_id"] != ""


def test_register_then_login_complete_flow(integration_client: TestClient):
    """Flujo 2: POST /register → POST /login — flujo completo con DB real."""
    # Step 1: Registro
    reg_response = integration_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Flow User",
            "email": "flow@example.com",
            "password": "SecurePass123!",
        },
    )
    assert reg_response.status_code == 201

    # Step 2: Login con las mismas credenciales
    login_response = integration_client.post(
        "/api/v1/auth/login",
        json={
            "email": "flow@example.com",
            "password": "SecurePass123!",
        },
    )

    assert login_response.status_code == 200
    data = login_response.json()
    assert "access_token" in data
    assert data["access_token"] is not None


def test_register_duplicate_email_returns_409(integration_client: TestClient):
    """Flujo 3: Registrar el mismo email dos veces retorna 409 Conflict."""
    payload = {
        "name": "Dup User",
        "email": "dup@example.com",
        "password": "SecurePass123!",
    }

    first = integration_client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = integration_client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


def test_login_unknown_email_returns_401(integration_client: TestClient):
    """Flujo 4: POST /login con email no registrado retorna 401."""
    response = integration_client.post(
        "/api/v1/auth/login",
        json={
            "email": "nobody@example.com",
            "password": "SecurePass123!",
        },
    )
    assert response.status_code == 401


def test_login_wrong_password_returns_401(integration_client: TestClient):
    """Flujo 5: POST /login con contraseña incorrecta retorna 401."""
    # Registrar usuario
    integration_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Wrong Pass User",
            "email": "wrongpass@example.com",
            "password": "CorrectPass123!",
        },
    )

    # Intentar login con contraseña incorrecta
    response = integration_client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrongpass@example.com",
            "password": "WrongPass999!",
        },
    )
    assert response.status_code == 401
