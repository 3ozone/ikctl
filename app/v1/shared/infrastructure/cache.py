"""Valkey/Redis client wrapper — shared/infrastructure/cache.py.

Valkey es un fork Redis-compatible, por lo que usamos redis-py (asyncio).

Uso en main.py (Composition Root):
    from app.v1.shared.infrastructure.cache import create_valkey_client, close_valkey_client

    valkey_client = create_valkey_client(settings.VALKEY_URL)

    # Al shutdown:
    await close_valkey_client(valkey_client)
"""
from redis.asyncio import Redis
from redis.asyncio.client import Redis as AsyncRedis


def create_valkey_client(url: str, *, decode_responses: bool = True) -> AsyncRedis:
    """Crea un cliente async Valkey/Redis a partir de una URL.

    Reutiliza conexiones internamente via connection pool.
    Compatible con Valkey y Redis >= 7.

    Args:
        url:              URL de conexión (ej: "redis://localhost:6379/0").
        decode_responses: Si True, decodifica bytes a str automáticamente.

    Returns:
        Cliente async Redis listo para operar.
    """
    return Redis.from_url(url, decode_responses=decode_responses)


async def close_valkey_client(client: AsyncRedis) -> None:
    """Cierra el cliente y libera el connection pool.

    Debe llamarse en el lifespan shutdown de FastAPI.

    Args:
        client: Cliente creado con create_valkey_client().
    """
    await client.aclose()
