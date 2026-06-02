"""SQLAlchemyKitRepository — Implementación SQLAlchemy del repositorio de kits."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.kits.application.interfaces.kit_repository import KitRepository
from app.v1.kits.domain.entities.kit import Kit
from app.v1.kits.domain.value_objects.sync_status import SyncStatus
from app.v1.kits.infrastructure.exceptions import DatabaseQueryError
from app.v1.kits.infrastructure.persistence.models import KitModel


class SQLAlchemyKitRepository(KitRepository):
    """Implementación SQLAlchemy del repositorio de kits."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Conversión entidad ↔ modelo
    # ------------------------------------------------------------------

    def _entity_to_model(self, kit: Kit) -> KitModel:
        return KitModel(
            id=kit.id,
            user_id=kit.user_id,
            repository_id=kit.repository_id,
            path_in_repo=kit.path_in_repo,
            name=kit.name,
            description=kit.description,
            version=kit.version,
            tags=kit.tags,          # list[str] — _JsonText serializa a JSON
            values=kit.values,      # dict     — _JsonText serializa a JSON
            debug_level=kit.debug_level,
            upload_files=list(kit.upload_files),
            pipeline_files=list(kit.pipeline_files),
            backup_files=list(kit.backup_files),
            sync_status=kit.sync_status.value,
            last_synced_at=kit.last_synced_at,
            last_commit_sha=kit.last_commit_sha,
            sync_error_message=kit.sync_error_message,
            is_deleted=kit.is_deleted,
            created_at=kit.created_at,
            updated_at=kit.updated_at,
        )

    def _model_to_entity(self, model: KitModel) -> Kit:
        return Kit(
            id=model.id,
            user_id=model.user_id,
            repository_id=model.repository_id,
            path_in_repo=model.path_in_repo,
            name=model.name,
            description=model.description,
            version=model.version,
            tags=model.tags or [],      # _JsonText deserializa a list[str]
            values=model.values or {},  # _JsonText deserializa a dict
            debug_level=model.debug_level,
            upload_files=tuple(model.upload_files or []),
            pipeline_files=tuple(model.pipeline_files or []),
            backup_files=tuple(model.backup_files or []),
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

    async def save(self, kit: Kit) -> None:
        """Persiste un nuevo kit.

        Raises:
            DatabaseQueryError: Si ocurre un error de persistencia.
        """
        try:
            model = self._entity_to_model(kit)
            self._session.add(model)
            await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            raise DatabaseQueryError(f"Error guardando kit: {exc}") from exc

    async def update(self, kit: Kit) -> None:
        """Actualiza los campos mutables de un kit existente.

        Raises:
            DatabaseQueryError: Si ocurre un error de persistencia.
        """
        try:
            result = await self._session.execute(
                select(KitModel).where(KitModel.id == kit.id)
            )
            model = result.scalar_one_or_none()
            if model is None:
                return
            model.name = kit.name
            model.description = kit.description
            model.version = kit.version
            model.tags = kit.tags
            model.values = kit.values
            model.debug_level = kit.debug_level
            model.sync_status = kit.sync_status.value
            model.last_synced_at = kit.last_synced_at
            model.last_commit_sha = kit.last_commit_sha
            model.sync_error_message = kit.sync_error_message
            model.is_deleted = kit.is_deleted
            model.updated_at = kit.updated_at
            await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            raise DatabaseQueryError(f"Error actualizando kit: {exc}") from exc

    # ------------------------------------------------------------------
    # Puerto — operaciones de lectura
    # ------------------------------------------------------------------

    async def find_by_id(self, kit_id: str, user_id: str) -> Optional[Kit]:
        """Busca un kit activo (is_deleted=False) por id y user_id.

        Raises:
            DatabaseQueryError: Si ocurre un error de consulta.
        """
        try:
            result = await self._session.execute(
                select(KitModel).where(
                    KitModel.id == kit_id,
                    KitModel.user_id == user_id,
                    KitModel.is_deleted.is_(False),
                )
            )
            model = result.scalar_one_or_none()
            return self._model_to_entity(model) if model else None
        except Exception as exc:
            raise DatabaseQueryError(f"Error buscando kit: {exc}") from exc

    async def find_by_id_internal(self, kit_id: str) -> Optional[Kit]:
        """Busca un kit por id sin filtro de usuario ni is_deleted.

        Usado internamente por use cases que acceden a kits eliminados
        o de cualquier usuario.

        Raises:
            DatabaseQueryError: Si ocurre un error de consulta.
        """
        try:
            result = await self._session.execute(
                select(KitModel).where(KitModel.id == kit_id)
            )
            model = result.scalar_one_or_none()
            return self._model_to_entity(model) if model else None
        except Exception as exc:
            raise DatabaseQueryError(f"Error buscando kit interno: {exc}") from exc

    async def find_by_repository_id(self, repository_id: str) -> list[Kit]:
        """Lista todos los kits de un repositorio, incluidos los borrados.

        Incluye is_deleted=True para que SyncRepository pueda reconciliar
        el estado entre la BD y el repositorio Git (RN-28).

        Raises:
            DatabaseQueryError: Si ocurre un error de consulta.
        """
        try:
            result = await self._session.execute(
                select(KitModel)
                .where(KitModel.repository_id == repository_id)
                .order_by(KitModel.created_at)
            )
            return [self._model_to_entity(m) for m in result.scalars().all()]
        except Exception as exc:
            raise DatabaseQueryError(
                f"Error listando kits del repositorio: {exc}"
            ) from exc

    async def find_all_by_user(
        self,
        user_id: str,
        page: int,
        per_page: int,
        tags_filter: list[str] | None = None,
        repository_id_filter: str | None = None,
    ) -> list[Kit]:
        """Lista kits activos de un usuario con paginación y filtros opcionales.

        El filtro de tags usa semántica AND: el kit debe contener TODOS los
        tags especificados. Como los tags se almacenan como JSON en texto,
        el filtrado se aplica en Python tras la consulta SQL.

        Raises:
            DatabaseQueryError: Si ocurre un error de consulta.
        """
        try:
            query = (
                select(KitModel)
                .where(
                    KitModel.user_id == user_id,
                    KitModel.is_deleted.is_(False),
                )
                .order_by(KitModel.created_at)
            )

            if repository_id_filter:
                query = query.where(KitModel.repository_id == repository_id_filter)

            if tags_filter:
                # Tags almacenados como JSON → filtro AND aplicado en Python
                result = await self._session.execute(query)
                all_kits = [self._model_to_entity(m) for m in result.scalars().all()]
                filtered = [
                    k for k in all_kits
                    if all(tag in k.tags for tag in tags_filter)
                ]
                offset = (page - 1) * per_page
                return filtered[offset: offset + per_page]

            offset = (page - 1) * per_page
            result = await self._session.execute(
                query.offset(offset).limit(per_page)
            )
            return [self._model_to_entity(m) for m in result.scalars().all()]

        except Exception as exc:
            raise DatabaseQueryError(f"Error listando kits: {exc}") from exc
