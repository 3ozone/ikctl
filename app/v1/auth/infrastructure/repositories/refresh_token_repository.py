"""Implementación de RefreshTokenRepository con SQLAlchemy."""
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import select, delete as sql_delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.auth.application.interfaces.refresh_token_repository import RefreshTokenRepository
from app.v1.auth.domain.entities import RefreshToken
from app.v1.auth.infrastructure.persistence.models import RefreshTokenModel
from app.v1.auth.infrastructure.exceptions import InfrastructureException


class SQLAlchemyRefreshTokenRepository(RefreshTokenRepository):
    """Implementación de repositorio de refresh tokens con SQLAlchemy async."""

    def __init__(self, session: AsyncSession) -> None:
        """Constructor del repositorio.

        Args:
            session: Session async de SQLAlchemy.
        """
        self.session = session

    async def save(self, token: RefreshToken) -> RefreshToken:
        """Persiste un refresh token.

        Args:
            token: Entidad RefreshToken.

        Returns:
            RefreshToken persistido.

        Raises:
            InfrastructureException: Error de persistencia.
        """
        try:
            model = RefreshTokenModel(
                id=token.id,
                user_id=token.user_id,
                token=token.token,
                expires_at=token.expires_at,
                created_at=token.created_at
            )
            self.session.add(model)
            await self.session.commit()
            await self.session.refresh(model)

            return token
        except Exception as e:
            await self.session.rollback()
            raise InfrastructureException(
                f"Error al guardar refresh token: {str(e)}"
            ) from e

    async def find_by_token(self, token: str) -> Optional[RefreshToken]:
        """Busca un refresh token por su valor.

        Args:
            token: Token JWT string.

        Returns:
            RefreshToken si existe, None si no.

        Raises:
            InfrastructureException: Error de consulta.
        """
        try:
            stmt = select(RefreshTokenModel).where(
                RefreshTokenModel.token == token)
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return RefreshToken(
                id=model.id,
                user_id=model.user_id,
                token=model.token,
                expires_at=model.expires_at,
                created_at=model.created_at
            )
        except Exception as e:
            raise InfrastructureException(
                f"Error al buscar refresh token: {str(e)}"
            ) from e

    async def delete(self, token: str) -> None:
        """Elimina (revoca) un refresh token.

        Args:
            token: Token JWT string a revocar.

        Raises:
            InfrastructureException: Error de eliminación.
        """
        try:
            stmt = sql_delete(RefreshTokenModel).where(
                RefreshTokenModel.token == token)
            await self.session.execute(stmt)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise InfrastructureException(
                f"Error al eliminar refresh token: {str(e)}"
            ) from e

    async def delete_by_user_id(self, user_id: str) -> None:
        """Elimina todos los refresh tokens de un usuario.

        Args:
            user_id: ID del usuario.

        Raises:
            InfrastructureException: Error de eliminación.
        """
        try:
            stmt = sql_delete(RefreshTokenModel).where(
                RefreshTokenModel.user_id == user_id)
            await self.session.execute(stmt)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise InfrastructureException(
                f"Error al eliminar tokens del usuario: {str(e)}"
            ) from e

    async def count_by_user_id(self, user_id: str) -> int:
        """Cuenta los tokens activos de un usuario.

        Args:
            user_id: ID del usuario.

        Returns:
            Número de tokens activos (no expirados).

        Raises:
            InfrastructureException: Error de consulta.
        """
        try:
            now = datetime.now(timezone.utc)
            # type: ignore necesario porque Pylance no reconoce func.count como callable
            stmt = select(func.count(RefreshTokenModel.id)).where(  # type: ignore
                RefreshTokenModel.user_id == user_id,  # type: ignore
                RefreshTokenModel.expires_at > now  # type: ignore
            )  # type: ignore
            result = await self.session.execute(stmt)
            count = result.scalar()
            return count or 0
        except Exception as e:
            raise InfrastructureException(
                f"Error al contar tokens del usuario: {str(e)}"
            ) from e

    async def find_by_user_id(self, user_id: str) -> List[RefreshToken]:
        """Obtiene todos los refresh tokens activos de un usuario.

        Args:
            user_id: ID del usuario.

        Returns:
            Lista de RefreshToken activos.

        Raises:
            InfrastructureException: Error de consulta.
        """
        try:
            now = datetime.now(timezone.utc)
            stmt = select(RefreshTokenModel).where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.expires_at > now
            ).order_by(RefreshTokenModel.created_at.desc())

            result = await self.session.execute(stmt)
            models = result.scalars().all()

            return [
                RefreshToken(
                    id=model.id,
                    user_id=model.user_id,
                    token=model.token,
                    expires_at=model.expires_at,
                    created_at=model.created_at
                )
                for model in models
            ]
        except Exception as e:
            raise InfrastructureException(
                f"Error al buscar tokens del usuario: {str(e)}"
            ) from e
