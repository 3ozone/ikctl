"""Query para listar repositorios Git de un usuario paginados."""
from app.v1.kits.application.dtos.repository_list_result import RepositoryListResult
from app.v1.kits.application.dtos.repository_result import RepositoryResult
from app.v1.kits.application.interfaces.repository_repository import RepositoryRepository


class ListRepositories:
    """Query para listar los repositorios Git de un usuario con paginación."""

    def __init__(self, repository_repository: RepositoryRepository | None = None) -> None:
        self._repository_repo = repository_repository

    async def execute(self, user_id: str, page: int, per_page: int) -> RepositoryListResult:
        """Lista los repositorios del usuario (solo no eliminados).

        Args:
            user_id: ID del usuario propietario
            page: Número de página (1-based)
            per_page: Elementos por página (máx 50)

        Returns:
            RepositoryListResult paginado con los repositorios del usuario
        """
        repositories = await self._repository_repo.find_all_by_user(user_id, page, per_page)

        items = [
            RepositoryResult(
                repository_id=repo.id,
                user_id=repo.user_id,
                url=repo.url,
                ref=repo.ref,
                credential_id=repo.credential_id,
                sync_status=repo.sync_status.value,
                last_synced_at=repo.last_synced_at,
                last_commit_sha=repo.last_commit_sha,
                sync_error_message=repo.sync_error_message,
                created_at=repo.created_at,
                updated_at=repo.updated_at,
            )
            for repo in repositories
        ]

        return RepositoryListResult(
            items=items,
            total=len(items),
            page=page,
            per_page=per_page,
        )
