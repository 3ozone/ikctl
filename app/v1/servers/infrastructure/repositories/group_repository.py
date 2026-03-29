"""SQLAlchemyGroupRepository — Implementación SQLAlchemy del repositorio de grupos."""
from typing import Optional

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.servers.application.interfaces.group_repository import GroupRepository
from app.v1.servers.domain.entities.group import Group
from app.v1.servers.infrastructure.exceptions import DatabaseQueryError
from app.v1.servers.infrastructure.persistence.models import GroupMemberModel, GroupModel


class SQLAlchemyGroupRepository(GroupRepository):
    """Implementación SQLAlchemy del repositorio de grupos de servidores.

    Los `server_ids` se persisten en la tabla `group_members` (relación N:M).
    """

    def __init__(self, session: AsyncSession) -> None:
        """Inicializa el repositorio con la sesión de base de datos.

        Args:
            session: Sesión async de SQLAlchemy.
        """
        self._session = session

    # ------------------------------------------------------------------
    # Helpers de conversión
    # ------------------------------------------------------------------

    async def _load_server_ids(self, group_id: str) -> list[str]:
        """Carga los server_ids del grupo desde group_members."""
        result = await self._session.execute(
            select(GroupMemberModel.server_id).where(
                GroupMemberModel.group_id == group_id
            )
        )
        return list(result.scalars().all())

    async def _save_members(self, group_id: str, server_ids: list[str]) -> None:
        """Persiste los miembros del grupo en group_members."""
        for server_id in server_ids:
            self._session.add(
                GroupMemberModel(group_id=group_id, server_id=server_id)
            )

    async def _replace_members(self, group_id: str, server_ids: list[str]) -> None:
        """Reemplaza todos los miembros del grupo por la nueva lista."""
        await self._session.execute(
            delete(GroupMemberModel).where(GroupMemberModel.group_id == group_id)
        )
        await self._save_members(group_id, server_ids)

    def _model_to_entity(self, model: GroupModel, server_ids: list[str]) -> Group:
        return Group(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            description=model.description,
            server_ids=server_ids,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    async def save(self, group: Group) -> None:
        """Persiste un nuevo grupo y sus miembros.

        Raises:
            DatabaseQueryError: Si falla la persistencia.
        """
        try:
            model = GroupModel(
                id=group.id,
                user_id=group.user_id,
                name=group.name,
                description=group.description,
                created_at=group.created_at,
                updated_at=group.updated_at,
            )
            self._session.add(model)
            await self._session.flush()
            await self._save_members(group.id, group.server_ids)
            await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            raise DatabaseQueryError(f"Error guardando grupo: {exc}") from exc

    async def find_by_id(self, group_id: str, user_id: str) -> Optional[Group]:
        """Busca un grupo por id scoped al usuario propietario.

        Returns:
            Group con sus server_ids, o None si no existe o no pertenece al usuario.

        Raises:
            DatabaseQueryError: Si falla la consulta.
        """
        try:
            result = await self._session.execute(
                select(GroupModel).where(
                    GroupModel.id == group_id,
                    GroupModel.user_id == user_id,
                )
            )
            model = result.scalar_one_or_none()
            if model is None:
                return None
            server_ids = await self._load_server_ids(group_id)
            return self._model_to_entity(model, server_ids)
        except Exception as exc:
            raise DatabaseQueryError(f"Error buscando grupo: {exc}") from exc

    async def find_all_by_user(
        self, user_id: str, page: int, per_page: int
    ) -> list[Group]:
        """Lista grupos de un usuario con paginación (1-based).

        Raises:
            DatabaseQueryError: Si falla la consulta.
        """
        try:
            offset = (page - 1) * per_page
            result = await self._session.execute(
                select(GroupModel)
                .where(GroupModel.user_id == user_id)
                .order_by(GroupModel.created_at)
                .offset(offset)
                .limit(per_page)
            )
            models = result.scalars().all()
            groups = []
            for model in models:
                server_ids = await self._load_server_ids(model.id)
                groups.append(self._model_to_entity(model, server_ids))
            return groups
        except Exception as exc:
            raise DatabaseQueryError(f"Error listando grupos: {exc}") from exc

    async def update(self, group: Group) -> None:
        """Actualiza los campos del grupo y reemplaza sus miembros.

        Raises:
            DatabaseQueryError: Si falla la persistencia.
        """
        try:
            result = await self._session.execute(
                select(GroupModel).where(GroupModel.id == group.id)
            )
            model = result.scalar_one_or_none()
            if model is None:
                return

            model.name = group.name
            model.description = group.description
            model.updated_at = group.updated_at

            await self._replace_members(group.id, group.server_ids)
            await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            raise DatabaseQueryError(f"Error actualizando grupo: {exc}") from exc

    async def delete(self, group_id: str) -> None:
        """Elimina un grupo y sus miembros (CASCADE por FK).

        Raises:
            DatabaseQueryError: Si falla la eliminación.
        """
        try:
            result = await self._session.execute(
                select(GroupModel).where(GroupModel.id == group_id)
            )
            model = result.scalar_one_or_none()
            if model:
                await self._session.delete(model)
                await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            raise DatabaseQueryError(f"Error eliminando grupo: {exc}") from exc

    async def has_active_pipeline_executions(self, group_id: str) -> bool:
        """Comprueba si el grupo tiene ejecuciones de pipeline activas.

        Consulta la tabla `pipeline_executions` por nombre ya que el módulo
        pipelines aún no expone sus modelos SQLAlchemy.

        Returns:
            True si tiene ejecuciones activas (pending/running), False si no.

        Raises:
            DatabaseQueryError: Si falla la consulta.
        """
        try:
            result = await self._session.execute(
                text(
                    "SELECT id FROM pipeline_executions "
                    "WHERE group_id = :group_id "
                    "AND status IN ('pending', 'running') "
                    "LIMIT 1"
                ),
                {"group_id": group_id},
            )
            return result.scalar_one_or_none() is not None
        except Exception as exc:
            raise DatabaseQueryError(
                f"Error comprobando ejecuciones activas: {exc}"
            ) from exc
