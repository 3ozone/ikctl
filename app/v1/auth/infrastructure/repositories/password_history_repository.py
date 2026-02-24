"""SQLAlchemyPasswordHistoryRepository - Implementación SQLAlchemy de PasswordHistoryRepository."""
from typing import List
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.auth.domain.entities import PasswordHistory
from app.v1.auth.application.interfaces.password_history_repository import PasswordHistoryRepository
from app.v1.auth.infrastructure.persistence.models import PasswordHistoryModel
from app.v1.auth.infrastructure.exceptions import InfrastructureException


class SQLAlchemyPasswordHistoryRepository(PasswordHistoryRepository):
    """Implementación SQLAlchemy del repositorio de historial de contraseñas."""

    def __init__(self, session: AsyncSession):
        """Inicializa el repositorio con la sesión de base de datos.

        Args:
            session: Sesión async de SQLAlchemy
        """
        self._session = session

    async def save(self, user_id: str, password_hash: str) -> None:
        """Guarda un hash de contraseña en el historial.

        Args:
            user_id: ID del usuario
            password_hash: Hash bcrypt de la contraseña

        Raises:
            InfrastructureException: Error de persistencia
        """
        try:
            history_model = PasswordHistoryModel(
                id=str(uuid4()),
                user_id=user_id,
                password_hash=password_hash,
                created_at=datetime.now(timezone.utc)
            )

            self._session.add(history_model)
            await self._session.commit()

        except Exception as e:
            await self._session.rollback()
            raise InfrastructureException(
                f"Error guardando historial de contraseña: {str(e)}"
            ) from e

    async def find_last_n_by_user(self, user_id: str, n: int) -> List[PasswordHistory]:
        """Obtiene las últimas N entradas de historial de contraseñas de un usuario.

        Args:
            user_id: ID del usuario
            n: Número de contraseñas a recuperar (3 para RN-07)

        Returns:
            Lista de PasswordHistory entities en orden descendente (más reciente primero)

        Raises:
            InfrastructureException: Error de consulta
        """
        try:
            result = await self._session.execute(
                select(PasswordHistoryModel)
                .where(PasswordHistoryModel.user_id == user_id)
                .order_by(desc(PasswordHistoryModel.created_at))
                .limit(n)
            )

            models = result.scalars().all()

            return [self._model_to_entity(model) for model in models]

        except Exception as e:
            raise InfrastructureException(
                f"Error consultando historial de contraseñas: {str(e)}"
            ) from e

    def _model_to_entity(self, model: PasswordHistoryModel) -> PasswordHistory:
        """Convierte PasswordHistoryModel a PasswordHistory entity.

        Args:
            model: Modelo de SQLAlchemy

        Returns:
            Entity PasswordHistory
        """
        return PasswordHistory(
            id=model.id,
            user_id=model.user_id,
            password_hash=model.password_hash,
            created_at=model.created_at
        )
