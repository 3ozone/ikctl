"""Query para obtener un kit por id."""
from app.v1.kits.application.dtos.kit_result import KitResult
from app.v1.kits.application.exceptions import KitNotFoundError
from app.v1.kits.application.interfaces.kit_repository import KitRepository


class GetKit:
    """Query para obtener un kit descubierto en un repositorio Git."""

    def __init__(self, kit_repository: KitRepository | None = None) -> None:
        self._kit_repo = kit_repository

    async def execute(self, user_id: str, kit_id: str) -> KitResult:
        """Obtiene un kit por id, validando ownership y que no esté eliminado.

        Args:
            user_id: ID del usuario propietario
            kit_id: ID del kit a obtener

        Returns:
            KitResult con los datos del kit

        Raises:
            KitNotFoundError: Si no existe, no pertenece al usuario o está eliminado (RN-01)
        """
        kit = await self._kit_repo.find_by_id(kit_id, user_id)
        if kit is None or kit.is_deleted:
            raise KitNotFoundError()

        return KitResult(
            kit_id=kit.id,
            user_id=kit.user_id,
            repository_id=kit.repository_id,
            path_in_repo=kit.path_in_repo,
            name=kit.name,
            description=kit.description,
            version=kit.version,
            tags=kit.tags,
            values=kit.values,
            debug_level=kit.debug_level,
            sync_status=kit.sync_status.value,
            last_synced_at=kit.last_synced_at,
            last_commit_sha=kit.last_commit_sha,
            sync_error_message=kit.sync_error_message,
            created_at=kit.created_at,
            updated_at=kit.updated_at,
        )
