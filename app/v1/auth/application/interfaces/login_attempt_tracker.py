"""
Interface para login attempt tracker service.

Define el contrato que será implementado en infrastructure/services/.
"""
from abc import ABC, abstractmethod


class LoginAttemptTracker(ABC):
    """Contrato para rastrear intentos de login fallidos (RN-04, RNF-08: bloqueo tras 5 intentos por 15 min)."""

    @abstractmethod
    async def record_failed_attempt(self, identifier: str) -> int:
        """
        Registra un intento de login fallido.

        Args:
            identifier: Identificador único del usuario (email, user_id, IP, etc.)

        Returns:
            Número total de intentos fallidos registrados

        Raises:
            InfrastructureException: Error al registrar el intento
        """

    @abstractmethod
    async def is_blocked(self, identifier: str) -> bool:
        """
        Verifica si un usuario está bloqueado por intentos fallidos.

        Args:
            identifier: Identificador único del usuario

        Returns:
            True si está bloqueado (más de 5 intentos), False si puede intentar login

        Raises:
            InfrastructureException: Error al verificar el estado de bloqueo
        """

    @abstractmethod
    async def reset_attempts(self, identifier: str) -> None:
        """
        Resetea el contador de intentos fallidos (tras login exitoso).

        Args:
            identifier: Identificador único del usuario

        Raises:
            InfrastructureException: Error al resetear el contador
        """

    @abstractmethod
    async def get_remaining_attempts(self, identifier: str) -> int:
        """
        Obtiene el número de intentos restantes antes del bloqueo.

        Args:
            identifier: Identificador único del usuario

        Returns:
            Número de intentos restantes (0 si está bloqueado, 5 si no hay intentos previos)

        Raises:
            InfrastructureException: Error al consultar intentos
        """
