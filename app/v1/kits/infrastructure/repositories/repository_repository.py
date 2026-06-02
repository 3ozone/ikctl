"""SQLAlchemyRepositoryRepository — Implementación SQLAlchemy del repositorio de repositorios Git."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.kits.application.interfaces.repository_repository import RepositoryRepository
from app.v1.kits.domain.entities.repository import Repository
from app.v1.kits.domain.value_objects.sync_status import SyncStatus
from app.v1.kits.infrastructure.exceptions import DatabaseQueryError
from app.v1.kits.infrastructure.persistence.models import KitModel, RepositoryModel


class SQLAlchemyRepositoryRepository(RepositoryRepository):
    """Implementación SQLAlchemy del repositorio de repositorios Git."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Conversión entidad ↔ modelo
    # ------------------------------------------------------------------

    def _entity_to_model(self, repository: Repository) -> RepositoryModel:
        return RepositoryModel(
            id=repository.id,
            user_id=repository.user_id,
            url=repository.url,
            ref=repository.ref,
            credential_id=repository.credential_id,
            sync_status=repository.sync_status.value,
            last_synced_at=repository.last_synced_at,
            last_commit_sha=repository.last_commit_sha,
            sync_error_message=repository.sync_error_message,
            is_deleted=repository.is_deleted,
            created_at=repository.created_at,
            updated_at=repository.updated_at,
        )

    def _model_to_entity(self, model: RepositoryModel) -> Repository:
        return Repository(
            id=model.id,
            user_id=model.user_id,
            url=model.url,
            ref=model.ref,
            credential_id=model.credential_id,
            sync_status=SyncStatus(model.sync_status),
            last_synced_at=model.last_synced_at,
            last_commit_sha=model.last_commit_sha,
            sync_error_message=model.sync_error_message,
            is_deleted=model.is_deleted,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ------------------------------------------------------------------
    # Puerto — operaciones de escritura
    # ------------------------------------------------------------------

    async def save(self, repository: Repository) -> None:
        """Persiste un nuevo repositorio.

        Raises:
            DatabaseQueryError: Si ocurre un error de persistencia.
        """
        try:
            model = self._entity_to_model(repository)
            self._session.add(model)
            await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            raise DatabaseQueryError(f"Error guardando repositorio: {exc}") from exc

    async def update(self, repository: Repository) -> None:
        """Actualiza los campos mutables de un repositorio existente.

        Raises:
            DatabaseQueryError: Si ocurre un error de persistencia.
        """
        try:
            result = await self._session.execute(
                select(RepositoryModel).where(RepositoryModel.id == repository.id)
            )
            model = result.scalar_one_or_none()
            if model is None:
                return
            model.url = repository.url
            model.ref = repository.ref
            model.credential_id = repository.credential_id
            model.sync_status = repository.sync_status.value
            model.last_synced_at = repository.last_synced_at
            model.last_commit_sha = repository.last_commit_sha
            model.sync_error_message = repository.sync_error_message
            model.is_deleted = repository.is_deleted
            model.updated_at = repository.updated_at
            await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            raise DatabaseQueryError(f"Error actualizando repositorio: {exc}") from exc

    async def delete(self, repository_id: str) -> None:
        """Elimina físicamente un repositorio por id.

        Raises:
            DatabaseQueryError: Si ocurre un error de persistencia.
        """
        try:
            result = await self._session.execute(
                select(RepositoryModel).where(RepositoryModel.id == repository_id)
            )
            model = result.scalar_one_or_none()
            if model:
                await self._session.delete(model)
                await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            raise DatabaseQueryError(f"Error eliminando repositorio: {exc}") from exc

    # ------------------------------------------------------------------
    # Puerto — operaciones de lectura
    # ------------------------------------------------------------------

    async def find_by_id(self, repository_id: str, user_id: str) -> Optional[Repository]:
        """Busca un repositorio activo (is_deleted=False) por id y user_id.

        Raises:
            DatabaseQueryError: Si ocurre un error de consulta.
        """
        try:
            result = await self._session.execute(
                select(RepositoryModel).where(
                    RepositoryModel.id == repository_id,
                    RepositoryModel.user_id == user_id,
                    RepositoryModel.is_deleted.is_(False),
                )
            )
            model = result.scalar_one_or_none()
            return self._model_to_entity(model) if model else None
        except Exception as exc:
            raise DatabaseQueryError(f"Error buscando repositorio: {exc}") from exc

    async def find_by_id_internal(self, repository_id: str) -> Optional[Repository]:
        """Busca un repositorio por id sin validar ownership ni is_deleted.

        Usado internamente por tasks (SSHKitExecutor) que no tienen contexto de usuario.

        Raises:
            DatabaseQueryError: Si ocurre un error de consulta.
        """
        try:
            result = await self._session.execute(
                select(RepositoryModel).where(
                    RepositoryModel.id == repository_id,
                )
            )
            model = result.scalar_one_or_none()
            return self._model_to_entity(model) if model else None
        except Exception as exc:
            raise DatabaseQueryError(f"Error buscando repositorio interno: {exc}") from exc

    async def find_all_by_user(
        self, user_id: str, page: int, per_page: int
    ) -> list[Repository]:
        """Lista repositorios activos de un usuario con paginación.

        Solo devuelve registros con is_deleted=False, ordenados por created_at.

        Raises:
            DatabaseQueryError: Si ocurre un error de consulta.
        """
        try:
            offset = (page - 1) * per_page
            result = await self._session.execute(
                select(RepositoryModel)
                .where(
                    RepositoryModel.user_id == user_id,
                    RepositoryModel.is_deleted.is_(False),
                )
                .order_by(RepositoryModel.created_at)
                .offset(offset)
                .limit(per_page)
            )
            return [self._model_to_entity(m) for m in result.scalars().all()]
        except Exception as exc:
            raise DatabaseQueryError(f"Error listando repositorios: {exc}") from exc

    async def find_all_active(self) -> list[Repository]:
        """Devuelve todos los repositorios activos (is_deleted=False) de todos los usuarios.

        Usado por PeriodicSyncRepositories para sincronizar el sistema entero.

        Raises:
            DatabaseQueryError: Si ocurre un error de consulta.
        """
        try:
            result = await self._session.execute(
                select(RepositoryModel)
                .where(RepositoryModel.is_deleted.is_(False))
                .order_by(RepositoryModel.created_at)
            )
            return [self._model_to_entity(m) for m in result.scalars().all()]
        except Exception as exc:
            raise DatabaseQueryError(f"Error listando todos los repositorios activos: {exc}") from exc

    async def has_kits_with_references(self, repository_id: str) -> bool:
        """Comprueba si el repositorio tiene kits activos (is_deleted=False).

        Protege el borrado físico del repositorio (RN-30): no se puede eliminar
        si aún quedan kits activos. En fases posteriores se extenderá para
        comprobar también referencias en operations y pipelines.

        Raises:
            DatabaseQueryError: Si ocurre un error de consulta.
        """
        try:
            result = await self._session.execute(
                select(KitModel.id)
                .where(
                    KitModel.repository_id == repository_id,
                    KitModel.is_deleted.is_(False),
                )
                .limit(1)
            )
            return result.scalar_one_or_none() is not None
        except Exception as exc:
            raise DatabaseQueryError(
                f"Error comprobando kits del repositorio: {exc}"
            ) from exc
