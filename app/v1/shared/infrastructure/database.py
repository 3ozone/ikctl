"""Session factory async para SQLAlchemy — shared/infrastructure/database.py.

Uso en main.py (Composition Root):
    from app.v1.shared.infrastructure.database import create_engine, create_session_factory, get_db_session

    engine = create_engine(settings.DB_URL)
    session_factory = create_session_factory(engine)

    # Dependencia FastAPI (scoped per request)
    async def get_db_session_dep():
        async for session in get_db_session(session_factory):
            yield session
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(db_url: str, *, echo: bool = False) -> AsyncEngine:
    """Crea el motor async de SQLAlchemy.

    Args:
        db_url: URL de conexión (ej: "mysql+aiomysql://user:pass@host/db").
        echo:   Si True, emite todas las sentencias SQL al log (solo desarrollo).

    Returns:
        AsyncEngine listo para usar.
    """
    return create_async_engine(db_url, echo=echo, future=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Crea la session factory vinculada al motor.

    Args:
        engine: AsyncEngine creado con create_engine().

    Returns:
        async_sessionmaker que produce AsyncSession por request.
    """
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Generador async que provee una AsyncSession por request y hace commit al finalizar.

    Uso con FastAPI Depends():
        async def dep(session=Depends(lambda: get_db_session(session_factory))):
            ...

    Si ocurre una excepción, SQLAlchemy hace rollback automático al cerrar el contexto.

    Args:
        session_factory: Factory creada con create_session_factory().

    Yields:
        AsyncSession scoped al request actual.
    """
    async with session_factory() as session:
        yield session
        await session.commit()
