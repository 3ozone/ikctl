"""
Interface para el repositorio de historial de contraseñas.

Define el contrato que será implementado en infrastructure/persistence/.
"""
from abc import ABC, abstractmethod
from typing import List
from app.v1.auth.domain.entities import PasswordHistory


class PasswordHistoryRepository(ABC):
    """Contrato para operaciones de historial de contraseñas (RN-07)."""

    @abstractmethod
    async def save(self, user_id: str, password_hash: str) -> None:
        """
        Guarda un hash de contraseña en el historial.

        Args:
            user_id: ID del usuario
            password_hash: Hash bcrypt de la contraseña

        Raises:
            InfrastructureException: Error de persistencia
        """

    @abstractmethod
    async def find_last_n_by_user(self, user_id: str, n: int) -> List[PasswordHistory]:
        """
        Obtiene las últimas N entradas de historial de contraseñas de un usuario.

        Args:
            user_id: ID del usuario
            n: Número de contraseñas a recuperar (3 para RN-07)

        Returns:
            Lista de PasswordHistory entities en orden descendente (más reciente primero)

        Raises:
            InfrastructureException: Error de consulta
        """
