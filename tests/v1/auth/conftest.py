"""Fixtures para tests de infrastructure."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.v1.auth.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from app.v1.auth.infrastructure.repositories.verification_token_repository import (
    SQLAlchemyVerificationTokenRepository
)

# Importar Base y modelos para crear tablas
from app.v1.auth.infrastructure.persistence.models import (
    Base,
    UserModel,
    RefreshTokenModel,
    VerificationTokenModel,
    PasswordHistoryModel
)
from app.v1.auth.infrastructure.repositories.refresh_token_repository import (
    SQLAlchemyRefreshTokenRepository
)


@pytest_asyncio.fixture
async def db_engine():
    """Crea engine SQLite in-memory para tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )

    # Crear todas las tablas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Crea session de base de datos para cada test."""
    async_session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def refresh_token_repository(db_session):
    """Fixture para RefreshTokenRepository con DB real."""
    return SQLAlchemyRefreshTokenRepository(db_session)


@pytest_asyncio.fixture
async def user_repository(db_session):
    """Fixture para UserRepository con DB real."""
    return SQLAlchemyUserRepository(db_session)


@pytest_asyncio.fixture
async def verification_token_repository(db_session):
    """Fixture para VerificationTokenRepository con DB real."""
    return SQLAlchemyVerificationTokenRepository(db_session)
