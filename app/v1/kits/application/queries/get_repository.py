"""Query para obtener un repositorio Git por id."""
from app.v1.kits.application.dtos.repository_result import RepositoryResult
from app.v1.kits.application.exceptions import RepositoryNotFoundError
from app.v1.kits.application.interfaces.repository_repository import RepositoryRepository


class GetRepository:
    """Query para obtener un repositorio Git del usuario."""

    def __init__(self, repository_repository: RepositoryRepository | None = None) -> None:
        self._repository_repo = repository_repository

    async def execute(self, user_id: str, repository_id: str) -> RepositoryResult:
        """Obtiene un repositorio por id, validando ownership y que no esté eliminado.

        Args:
            user_id: ID del usuario propietario
            repository_id: ID del repositorio a obtener

        Returns:
            RepositoryResult con los datos del repositorio

        Raises:
            RepositoryNotFoundError: Si no existe, no pertenece al usuario o está eliminado (RN-01)
        """
        repository = await self._repository_repo.find_by_id(repository_id, user_id)
        if repository is None or repository.is_deleted:
            raise RepositoryNotFoundError()

        return RepositoryResult(
            repository_id=repository.id,
            user_id=repository.user_id,
            url=repository.url,
            ref=repository.ref,
            credential_id=repository.credential_id,
            sync_status=repository.sync_status.value,
            last_synced_at=repository.last_synced_at,
            last_commit_sha=repository.last_commit_sha,
            sync_error_message=repository.sync_error_message,
            created_at=repository.created_at,
            updated_at=repository.updated_at,
        )
