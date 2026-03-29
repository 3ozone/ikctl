"""SQLAlchemyServerRepository — Implementación SQLAlchemy del repositorio de servidores."""
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.servers.application.interfaces.server_repository import ServerRepository
from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.infrastructure.exceptions import DatabaseQueryError
from app.v1.servers.infrastructure.persistence.models import ServerModel


class SQLAlchemyServerRepository(ServerRepository):
    """Implementación SQLAlchemy del repositorio de servidores."""

    def __init__(self, session: AsyncSession) -> None:
        """Inicializa el repositorio con la sesión de base de datos.

        Args:
            session: Sesión async de SQLAlchemy.
        """
        self._session = session

    # ------------------------------------------------------------------
    # Helpers de conversión
    # ------------------------------------------------------------------

    def _entity_to_model(self, server: Server) -> ServerModel:
        return ServerModel(
            id=server.id,
            user_id=server.user_id,
            name=server.name,
            type=server.type.value,
            status=server.status.value,
            host=server.host,
            port=server.port,
            credential_id=server.credential_id,
            description=server.description,
            os_id=server.os_id,
            os_version=server.os_version,
            os_name=server.os_name,
            created_at=server.created_at,
            updated_at=server.updated_at,
        )

    def _model_to_entity(self, model: ServerModel) -> Server:
        return Server(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            type=ServerType(model.type),
            status=ServerStatus(model.status),
            host=model.host,
            port=model.port,
            credential_id=model.credential_id,
            description=model.description,
            os_id=model.os_id,
            os_version=model.os_version,
            os_name=model.os_name,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    async def save(self, server: Server) -> None:
        """Persiste un nuevo servidor.

        Raises:
            DatabaseQueryError: Si falla la persistencia.
        """
        try:
            model = self._entity_to_model(server)
            self._session.add(model)
            await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            raise DatabaseQueryError(f"Error guardando servidor: {exc}") from exc

    async def find_by_id(self, server_id: str, user_id: str) -> Optional[Server]:
        """Busca un servidor por id scoped al usuario propietario.

        Returns:
            Server si existe y pertenece al usuario, None si no.

        Raises:
            DatabaseQueryError: Si falla la consulta.
        """
        try:
            result = await self._session.execute(
                select(ServerModel).where(
                    ServerModel.id == server_id,
                    ServerModel.user_id == user_id,
                )
            )
            model = result.scalar_one_or_none()
            return self._model_to_entity(model) if model else None
        except Exception as exc:
            raise DatabaseQueryError(f"Error buscando servidor: {exc}") from exc

    async def find_all_by_user(
        self, user_id: str, page: int, per_page: int
    ) -> list[Server]:
        """Lista servidores de un usuario con paginación (1-based).

        Raises:
            DatabaseQueryError: Si falla la consulta.
        """
        try:
            offset = (page - 1) * per_page
            result = await self._session.execute(
                select(ServerModel)
                .where(ServerModel.user_id == user_id)
                .order_by(ServerModel.created_at)
                .offset(offset)
                .limit(per_page)
            )
            return [self._model_to_entity(m) for m in result.scalars().all()]
        except Exception as exc:
            raise DatabaseQueryError(f"Error listando servidores: {exc}") from exc

    async def update(self, server: Server) -> None:
        """Actualiza los campos de un servidor existente.

        Raises:
            DatabaseQueryError: Si falla la persistencia.
        """
        try:
            result = await self._session.execute(
                select(ServerModel).where(ServerModel.id == server.id)
            )
            model = result.scalar_one_or_none()
            if model is None:
                return

            model.name = server.name
            model.status = server.status.value
            model.host = server.host
            model.port = server.port
            model.credential_id = server.credential_id
            model.description = server.description
            model.os_id = server.os_id
            model.os_version = server.os_version
            model.os_name = server.os_name
            model.updated_at = server.updated_at

            await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            raise DatabaseQueryError(f"Error actualizando servidor: {exc}") from exc

    async def delete(self, server_id: str) -> None:
        """Elimina un servidor por id.

        Raises:
            DatabaseQueryError: Si falla la eliminación.
        """
        try:
            result = await self._session.execute(
                select(ServerModel).where(ServerModel.id == server_id)
            )
            model = result.scalar_one_or_none()
            if model:
                await self._session.delete(model)
                await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            raise DatabaseQueryError(f"Error eliminando servidor: {exc}") from exc

    async def find_local_by_user(self, user_id: str) -> list[Server]:
        """Lista todos los servidores locales de un usuario.

        Raises:
            DatabaseQueryError: Si falla la consulta.
        """
        try:
            result = await self._session.execute(
                select(ServerModel).where(
                    ServerModel.user_id == user_id,
                    ServerModel.type == "local",
                )
            )
            return [self._model_to_entity(m) for m in result.scalars().all()]
        except Exception as exc:
            raise DatabaseQueryError(f"Error buscando servidores locales: {exc}") from exc

    async def has_active_operations(self, server_id: str) -> bool:
        """Comprueba si el servidor tiene operaciones activas (pending o running).

        Consulta la tabla `operations` por nombre ya que el módulo operations
        aún no expone sus modelos SQLAlchemy. Se actualiza cuando ese módulo
        implemente sus modelos.

        Returns:
            True si tiene operaciones activas, False si no.

        Raises:
            DatabaseQueryError: Si falla la consulta.
        """
        try:
            result = await self._session.execute(
                text(
                    "SELECT id FROM operations "
                    "WHERE server_id = :server_id "
                    "AND status IN ('pending', 'running') "
                    "LIMIT 1"
                ),
                {"server_id": server_id},
            )
            return result.scalar_one_or_none() is not None
        except Exception as exc:
            raise DatabaseQueryError(
                f"Error comprobando operaciones activas: {exc}"
            ) from exc
