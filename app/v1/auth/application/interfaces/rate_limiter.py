"""
Interface para rate limiter service.

Define el contrato que será implementado en infrastructure/services/.
"""
from abc import ABC, abstractmethod


class RateLimiter(ABC):
    """Contrato para servicio de rate limiting (RNF-09: 10 req/min en login)."""

    @abstractmethod
    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """
        Verifica si una request está permitida bajo el límite de rate.

        Args:
            key: Identificador único del recurso (ej: "login:192.168.1.1", "api:user_123")
            max_requests: Número máximo de requests permitidas en el window
            window_seconds: Ventana de tiempo en segundos para el límite

        Returns:
            True si la request está permitida (bajo el límite), False si excede el límite

        Raises:
            InfrastructureException: Error al consultar el rate limiter
        """

    @abstractmethod
    async def increment(
        self,
        key: str,
        window_seconds: int
    ) -> int:
        """
        Incrementa el contador de requests para una key.

        Args:
            key: Identificador único del recurso
            window_seconds: TTL para el contador (ventana de tiempo)

        Returns:
            Número actual de requests después del incremento

        Raises:
            InfrastructureException: Error al incrementar el contador
        """
