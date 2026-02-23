"""UserRepositoryImpl - Implementación SQLAlchemy de IUserRepository."""
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email
from app.v1.auth.application.interfaces.user_repository import IUserRepository
from app.v1.auth.application.exceptions import ResourceNotFoundError
from app.v1.auth.infrastructure.persistence.models import UserModel
from app.v1.auth.infrastructure.exceptions import InfrastructureException


class UserRepositoryImpl(IUserRepository):
    """Implementación SQLAlchemy del repositorio de usuarios."""

    def __init__(self, session: AsyncSession):
        """Inicializa el repositorio con la sesión de base de datos.

        Args:
            session: Sesión async de SQLAlchemy
        """
        self._session = session

    async def save(self, user: User) -> User:
        """Guarda un usuario en la base de datos.

        Args:
            user: Entidad User a persistir

        Returns:
            Usuario guardado con datos actualizados

        Raises:
            InfrastructureException: Si ocurre un error de persistencia
        """
        try:
            user_model = UserModel(
                id=user.id,
                name=user.name,
                email=user.email.value,
                password_hash=user.password_hash,
                totp_secret=user.totp_secret,
                is_2fa_enabled=user.is_2fa_enabled,
                created_at=user.created_at,
                updated_at=user.updated_at
            )

            self._session.add(user_model)
            await self._session.commit()
            await self._session.refresh(user_model)

            return self._model_to_entity(user_model)

        except Exception as e:
            await self._session.rollback()
            raise InfrastructureException(
                f"Error guardando usuario: {str(e)}") from e

    async def find_by_email(self, email: str) -> Optional[User]:
        """Busca un usuario por email.

        Args:
            email: Email a buscar

        Returns:
            Usuario si existe, None si no

        Raises:
            InfrastructureException: Si ocurre un error de consulta
        """
        try:
            result = await self._session.execute(
                select(UserModel).where(UserModel.email == email)
            )
            user_model = result.scalar_one_or_none()

            return self._model_to_entity(user_model) if user_model else None

        except Exception as e:
            raise InfrastructureException(
                f"Error buscando usuario por email: {str(e)}") from e

    async def find_by_id(self, user_id: str) -> Optional[User]:
        """Busca un usuario por ID.

        Args:
            user_id: ID del usuario

        Returns:
            Usuario si existe, None si no

        Raises:
            InfrastructureException: Si ocurre un error de consulta
        """
        try:
            result = await self._session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
            user_model = result.scalar_one_or_none()

            return self._model_to_entity(user_model) if user_model else None

        except Exception as e:
            raise InfrastructureException(
                f"Error buscando usuario por ID: {str(e)}") from e

    async def update(self, user: User) -> User:
        """Actualiza un usuario existente.

        Args:
            user: Usuario con datos actualizados

        Returns:
            Usuario actualizado

        Raises:
            ResourceNotFoundError: Si el usuario no existe
            InfrastructureException: Si ocurre un error de persistencia
        """
        try:
            result = await self._session.execute(
                select(UserModel).where(UserModel.id == user.id)
            )
            user_model = result.scalar_one_or_none()

            if not user_model:
                raise ResourceNotFoundError(
                    f"Usuario con ID {user.id} no encontrado")

            # Actualizar campos
            user_model.name = user.name
            user_model.email = user.email.value
            user_model.password_hash = user.password_hash
            user_model.totp_secret = user.totp_secret
            user_model.is_2fa_enabled = user.is_2fa_enabled
            user_model.updated_at = user.updated_at

            await self._session.commit()
            await self._session.refresh(user_model)

            return self._model_to_entity(user_model)

        except ResourceNotFoundError:
            raise
        except Exception as e:
            await self._session.rollback()
            raise InfrastructureException(
                f"Error actualizando usuario: {str(e)}") from e

    async def delete(self, user_id: str) -> None:
        """Elimina un usuario por ID.

        Args:
            user_id: ID del usuario a eliminar

        Raises:
            ResourceNotFoundError: Si el usuario no existe
            InfrastructureException: Si ocurre un error de eliminación
        """
        try:
            # Verificar que existe
            result = await self._session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
            user_model = result.scalar_one_or_none()

            if not user_model:
                raise ResourceNotFoundError(
                    f"Usuario con ID {user_id} no encontrado")

            # Eliminar
            await self._session.execute(
                delete(UserModel).where(UserModel.id == user_id)
            )
            await self._session.commit()

        except ResourceNotFoundError:
            raise
        except Exception as e:
            await self._session.rollback()
            raise InfrastructureException(
                f"Error eliminando usuario: {str(e)}") from e

    @staticmethod
    def _model_to_entity(model: UserModel) -> User:
        """Convierte un modelo SQLAlchemy a entidad de dominio.

        Args:
            model: Modelo UserModel

        Returns:
            Entidad User
        """
        return User(
            id=model.id,
            name=model.name,
            email=Email(model.email),
            password_hash=model.password_hash,
            totp_secret=model.totp_secret,
            is_2fa_enabled=model.is_2fa_enabled,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
