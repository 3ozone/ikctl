"""Fixtures para tests de infraestructura del módulo operations."""
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.v1.operations.infrastructure.persistence.models import Base


@pytest_asyncio.fixture
async def db_engine():
    """Engine SQLite in-memory para tests de operations."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Sesión de base de datos aislada para cada test."""
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def operation_repository(db_session):
    from app.v1.operations.infrastructure.repositories.operation_repository import (
        SQLAlchemyOperationRepository,
    )

    return SQLAlchemyOperationRepository(db_session)


@pytest_asyncio.fixture
async def file_cache_repository(db_session):
    from app.v1.operations.infrastructure.repositories.file_cache_repository import (
        SQLAlchemyFileCacheRepository,
    )

    return SQLAlchemyFileCacheRepository(db_session)
