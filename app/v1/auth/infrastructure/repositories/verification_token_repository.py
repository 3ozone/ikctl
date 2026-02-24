"""SQLAlchemyVerificationTokenRepository - Implementación SQLAlchemy de VerificationTokenRepository."""
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.auth.domain.entities import VerificationToken
from app.v1.auth.application.interfaces.verification_token_repository import (
    VerificationTokenRepository
)
from app.v1.auth.infrastructure.persistence.models import VerificationTokenModel
from app.v1.auth.infrastructure.exceptions import InfrastructureException


class SQLAlchemyVerificationTokenRepository(VerificationTokenRepository):
    """Implementación SQLAlchemy del repositorio de tokens de verificación."""

    def __init__(self, session: AsyncSession):
        """Inicializa el repositorio con la sesión de base de datos.

        Args:
            session: Sesión async de SQLAlchemy
        """
        self._session = session

    async def save(self, token: VerificationToken) -> VerificationToken:
        """Persiste un token de verificación.

        Args:
            token: Entidad VerificationToken a persistir

        Returns:
            Token guardado con datos actualizados

        Raises:
            InfrastructureException: Si ocurre un error de persistencia
        """
        try:
            token_model = VerificationTokenModel(
                id=token.id,
                user_id=token.user_id,
                token=token.token,
                token_type=token.token_type,
                expires_at=token.expires_at,
                created_at=token.created_at
            )

            self._session.add(token_model)
            await self._session.commit()
            await self._session.refresh(token_model)

            return self._model_to_entity(token_model)

        except Exception as e:
            await self._session.rollback()
            raise InfrastructureException(
                f"Error guardando verification token: {str(e)}") from e

    async def find_by_token(self, token: str) -> Optional[VerificationToken]:
        """Busca un token de verificación por su valor.

        Args:
            token: Token string a buscar

        Returns:
            VerificationToken si existe, None si no

        Raises:
            InfrastructureException: Si ocurre un error de consulta
        """
        try:
            result = await self._session.execute(
                select(VerificationTokenModel).where(
                    VerificationTokenModel.token == token
                )
            )
            token_model = result.scalar_one_or_none()

            return self._model_to_entity(token_model) if token_model else None

        except Exception as e:
            raise InfrastructureException(
                f"Error buscando verification token: {str(e)}") from e

    async def delete(self, token: str) -> None:
        """Elimina un token de verificación.

        Args:
            token: Token string a eliminar

        Raises:
            InfrastructureException: Si ocurre un error de eliminación
        """
        try:
            await self._session.execute(
                delete(VerificationTokenModel).where(
                    VerificationTokenModel.token == token
                )
            )
            await self._session.commit()

        except Exception as e:
            await self._session.rollback()
            raise InfrastructureException(
                f"Error eliminando verification token: {str(e)}") from e

    async def delete_by_user_id(self, user_id: str, token_type: str) -> None:
        """Elimina todos los tokens de un tipo para un usuario.

        Args:
            user_id: ID del usuario
            token_type: Tipo de token ('email_verification', 'password_reset')

        Raises:
            InfrastructureException: Si ocurre un error de eliminación
        """
        try:
            await self._session.execute(
                delete(VerificationTokenModel).where(
                    VerificationTokenModel.user_id == user_id,
                    VerificationTokenModel.token_type == token_type
                )
            )
            await self._session.commit()

        except Exception as e:
            await self._session.rollback()
            raise InfrastructureException(
                f"Error eliminando tokens del usuario: {str(e)}") from e

    @staticmethod
    def _model_to_entity(model: VerificationTokenModel) -> VerificationToken:
        """Convierte un modelo SQLAlchemy a entidad de dominio.

        Args:
            model: Modelo VerificationTokenModel

        Returns:
            Entidad VerificationToken
        """
        return VerificationToken(
            id=model.id,
            user_id=model.user_id,
            token=model.token,
            token_type=model.token_type,
            expires_at=model.expires_at,
            created_at=model.created_at
        )
