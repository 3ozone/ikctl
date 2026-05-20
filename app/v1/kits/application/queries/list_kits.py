"""Query para listar kits de un usuario paginados con filtros opcionales."""
from app.v1.kits.application.dtos.kit_list_result import KitListResult
from app.v1.kits.application.dtos.kit_result import KitResult
from app.v1.kits.application.interfaces.kit_repository import KitRepository


class ListKits:
    """Query para listar los kits de un usuario con paginación y filtros opcionales."""

    def __init__(self, kit_repository: KitRepository | None = None) -> None:
        self._kit_repo = kit_repository

    async def execute(
        self,
        user_id: str,
        page: int,
        per_page: int,
        tags_filter: list[str] | None = None,
        repository_id_filter: str | None = None,
    ) -> KitListResult:
        """Lista los kits del usuario (solo no eliminados) con filtros opcionales.

        Args:
            user_id: ID del usuario propietario
            page: Número de página (1-based)
            per_page: Elementos por página (máx 50)
            tags_filter: Lista de tags para filtrar (AND semántico), None = sin filtro
            repository_id_filter: ID de repositorio para filtrar, None = sin filtro

        Returns:
            KitListResult paginado con los kits del usuario que cumplen los filtros
        """
        kits = await self._kit_repo.find_all_by_user(
            user_id, page, per_page, tags_filter, repository_id_filter
        )

        items = [
            KitResult(
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
            for kit in kits
        ]

        return KitListResult(
            items=items,
            total=len(items),
            page=page,
            per_page=per_page,
        )
