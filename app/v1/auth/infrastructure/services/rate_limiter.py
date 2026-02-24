"""ValkeyRateLimiter - Implementación de RateLimiter usando Valkey.

Rate limiter service usando Valkey para almacenamiento de contadores con TTL.
"""
from typing import Any

from app.v1.auth.application.interfaces.rate_limiter import RateLimiter
from app.v1.auth.infrastructure.exceptions import InfrastructureException


class ValkeyRateLimiter(RateLimiter):
    """Implementación de RateLimiter usando Valkey (Redis-compatible) para contadores."""

    def __init__(self, valkey_client: Any):
        """Inicializa el rate limiter con cliente Valkey.

        Args:
            valkey_client: Cliente Valkey/Redis async (ej: redis.asyncio.Redis)
        """
        self._client = valkey_client

    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """Verifica si una request está permitida bajo el límite de rate.

        Args:
            key: Identificador único del recurso (ej: "login:192.168.1.1")
            max_requests: Número máximo de requests permitidas en el window
            window_seconds: Ventana de tiempo en segundos para el límite

        Returns:
            True si la request está permitida (bajo o en el límite), False si excede

        Raises:
            InfrastructureException: Error al consultar Valkey
        """
        try:
            # Obtener contador actual
            full_key = f"ratelimit:{key}"
            current_count = await self._client.get(full_key)

            # Si la key no existe, es el primer request (permitido)
            if current_count is None:
                return True

            # Convertir a int y verificar límite
            count = int(current_count)
            return count <= max_requests

        except Exception as e:
            raise InfrastructureException(
                f"Rate limiter check failed for key '{key}': {str(e)}"
            ) from e

    async def increment(
        self,
        key: str,
        window_seconds: int
    ) -> int:
        """Incrementa el contador de requests para una key.

        Args:
            key: Identificador único del recurso
            window_seconds: TTL para el contador (ventana de tiempo)

        Returns:
            Número actual de requests después del incremento

        Raises:
            InfrastructureException: Error al incrementar el contador en Valkey
        """
        try:
            full_key = f"ratelimit:{key}"

            # Incrementar contador (crea key si no existe, con valor inicial 1)
            count = await self._client.incr(full_key)

            # Si es el primer incremento (count=1), establecer TTL
            # Verificar si la key tiene TTL antes de asignarlo
            ttl = await self._client.ttl(full_key)
            if ttl == -1:  # -1 significa que no tiene TTL
                await self._client.expire(full_key, window_seconds)

            return count

        except Exception as e:
            raise InfrastructureException(
                f"Rate limiter increment failed for key '{key}': {str(e)}"
            ) from e
