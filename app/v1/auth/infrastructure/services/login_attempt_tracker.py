"""ValkeyLoginAttemptTracker - Implementación de LoginAttemptTracker usando Valkey.

Service para rastrear intentos de login fallidos y bloquear temporalmente usuarios.
RN-04: Bloqueo tras 5 intentos, RNF-08: Bloqueo temporal de 15 minutos.
"""
from typing import Any

from app.v1.auth.application.interfaces.login_attempt_tracker import LoginAttemptTracker
from app.v1.auth.infrastructure.exceptions import InfrastructureException


class ValkeyLoginAttemptTracker(LoginAttemptTracker):
    """Implementación de LoginAttemptTracker usando Valkey para almacenamiento de contadores."""

    # Configuración según RN-04 y RNF-08
    MAX_ATTEMPTS = 5
    BLOCK_DURATION_SECONDS = 900  # 15 minutos

    def __init__(self, valkey_client: Any):
        """Inicializa el tracker con cliente Valkey.

        Args:
            valkey_client: Cliente Valkey/Redis async (ej: redis.asyncio.Redis)
        """
        self._client = valkey_client

    async def record_failed_attempt(self, identifier: str) -> int:
        """Registra un intento de login fallido.

        Args:
            identifier: Identificador único del usuario (email, user_id, etc.)

        Returns:
            Número total de intentos fallidos registrados

        Raises:
            InfrastructureException: Error al registrar el intento en Valkey
        """
        try:
            key = f"login_attempts:{identifier}"

            # Incrementar contador
            count = await self._client.incr(key)

            # Si es el primer intento, establecer TTL
            ttl = await self._client.ttl(key)
            if ttl == -1:  # No tiene TTL
                await self._client.expire(key, self.BLOCK_DURATION_SECONDS)

            return count

        except Exception as e:
            raise InfrastructureException(
                f"Failed to record login attempt for '{identifier}': {str(e)}"
            ) from e

    async def is_blocked(self, identifier: str) -> bool:
        """Verifica si un usuario está bloqueado por intentos fallidos.

        Args:
            identifier: Identificador único del usuario

        Returns:
            True si está bloqueado (más de 5 intentos), False si puede intentar login

        Raises:
            InfrastructureException: Error al verificar el estado de bloqueo
        """
        try:
            key = f"login_attempts:{identifier}"
            count_str = await self._client.get(key)

            # Si no existe la key, no hay intentos fallidos
            if count_str is None:
                return False

            count = int(count_str)

            # Bloqueado si supera el límite (más de 5)
            return count > self.MAX_ATTEMPTS

        except Exception as e:
            raise InfrastructureException(
                f"Failed to check login block status for '{identifier}': {str(e)}"
            ) from e

    async def reset_attempts(self, identifier: str) -> None:
        """Resetea el contador de intentos fallidos (tras login exitoso).

        Args:
            identifier: Identificador único del usuario

        Raises:
            InfrastructureException: Error al resetear el contador
        """
        try:
            key = f"login_attempts:{identifier}"
            await self._client.delete(key)

        except Exception as e:
            raise InfrastructureException(
                f"Failed to reset login attempts for '{identifier}': {str(e)}"
            ) from e

    async def get_remaining_attempts(self, identifier: str) -> int:
        """Obtiene el número de intentos restantes antes del bloqueo.

        Args:
            identifier: Identificador único del usuario

        Returns:
            Número de intentos restantes (0 si está bloqueado, 5 si no hay intentos previos)

        Raises:
            InfrastructureException: Error al consultar intentos
        """
        try:
            key = f"login_attempts:{identifier}"
            count_str = await self._client.get(key)

            # Sin intentos previos
            if count_str is None:
                return self.MAX_ATTEMPTS

            count = int(count_str)

            # Si ya está bloqueado, 0 intentos restantes
            if count > self.MAX_ATTEMPTS:
                return 0

            # Calcular restantes
            return self.MAX_ATTEMPTS - count

        except Exception as e:
            raise InfrastructureException(
                f"Failed to get remaining attempts for '{identifier}': {str(e)}"
            ) from e
