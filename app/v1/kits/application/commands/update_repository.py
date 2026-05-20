"""Use Case para actualizar un repositorio Git existente."""
from typing import Optional

from app.v1.kits.application.dtos.repository_result import RepositoryResult
from app.v1.kits.application.exceptions import (
    InvalidGitCredentialTypeError,
    RepositoryNotFoundError,
)
from app.v1.kits.application.interfaces.repository_repository import RepositoryRepository
from app.v1.servers.application.interfaces.credential_repository import CredentialRepository

_GIT_CREDENTIAL_TYPES = {"git_https", "git_ssh"}


class UpdateRepository:
    """Use Case para actualizar los datos de un repositorio Git."""

    def __init__(
        self,
        repository_repository: RepositoryRepository | None = None,
        credential_repository: CredentialRepository | None = None,
    ) -> None:
        self._repository_repo = repository_repository
        self._credential_repo = credential_repository

    async def execute(
        self,
        user_id: str,
        repository_id: str,
        url: str,
        ref: str,
        correlation_id: str,
        credential_id: Optional[str] = None,
    ) -> RepositoryResult:
        """Actualiza los datos de un repositorio Git.

        Si cambia url o ref, la entity resetea sync_status a never_synced
        automáticamente via repo.update() (RN en entity).

        Args:
            user_id: ID del usuario propietario
            repository_id: ID del repositorio a actualizar
            url: Nueva URL del repositorio Git
            ref: Nueva rama, tag o commit SHA
            correlation_id: ID de trazabilidad del request
            credential_id: Nueva credencial Git opcional (solo git_https o git_ssh)

        Returns:
            RepositoryResult con los datos actualizados

        Raises:
            RepositoryNotFoundError: Si el repositorio no existe o no pertenece al usuario (RN-01)
            InvalidGitCredentialTypeError: Si la credencial no es de tipo git_https o git_ssh (RN-23)
        """
        repository = await self._repository_repo.find_by_id(repository_id, user_id)
        if repository is None:
            raise RepositoryNotFoundError()

        if credential_id is not None and self._credential_repo is not None:
            credential = await self._credential_repo.find_by_id(credential_id, user_id)
            if credential is not None and credential.type.value not in _GIT_CREDENTIAL_TYPES:
                raise InvalidGitCredentialTypeError()

        repository.update(url=url, ref=ref, credential_id=credential_id)

        await self._repository_repo.update(repository)

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
