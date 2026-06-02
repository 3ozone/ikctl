"""SQLAlchemyFileCacheRepository — Implementación SQLAlchemy de la caché de ficheros."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.operations.application.interfaces.file_cache_repository import FileCacheRepository
from app.v1.operations.infrastructure.persistence.models import ServerKitFileCacheModel


class SQLAlchemyFileCacheRepository(FileCacheRepository):
    """Implementación SQLAlchemy de la caché SHA-256 de ficheros SFTP."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_hash(
        self, server_id: str, kit_id: str, filename: str
    ) -> Optional[str]:
        """Devuelve el SHA-256 almacenado para (server_id, kit_id, filename), o None."""
        result = await self._session.execute(
            select(ServerKitFileCacheModel).where(
                ServerKitFileCacheModel.server_id == server_id,
                ServerKitFileCacheModel.kit_id == kit_id,
                ServerKitFileCacheModel.filename == filename,
            )
        )
        model = result.scalar_one_or_none()
        return model.content_hash if model else None

    async def upsert(
        self,
        server_id: str,
        kit_id: str,
        filename: str,
        content_hash: str,
    ) -> None:
        """Inserta o actualiza el hash para (server_id, kit_id, filename).

        El commit/rollback se gestiona en el scoped session (UoW).
        """
        result = await self._session.execute(
            select(ServerKitFileCacheModel).where(
                ServerKitFileCacheModel.server_id == server_id,
                ServerKitFileCacheModel.kit_id == kit_id,
                ServerKitFileCacheModel.filename == filename,
            )
        )
        model = result.scalar_one_or_none()
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if model is None:
            model = ServerKitFileCacheModel(
                server_id=server_id,
                kit_id=kit_id,
                filename=filename,
                content_hash=content_hash,
                uploaded_at=now,
            )
            self._session.add(model)
        else:
            model.content_hash = content_hash
            model.uploaded_at = now

    async def invalidate_server_kit(self, server_id: str, kit_id: str) -> None:
        """Elimina todas las entradas de caché para (server_id, kit_id).

        El commit/rollback se gestiona en el scoped session (UoW).
        """
        await self._session.execute(
            delete(ServerKitFileCacheModel).where(
                ServerKitFileCacheModel.server_id == server_id,
                ServerKitFileCacheModel.kit_id == kit_id,
            )
        )
