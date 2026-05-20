"""Use Case para registrar un nuevo repositorio Git como fuente de kits."""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.v1.kits.application.dtos.repository_result import RepositoryResult
from app.v1.kits.application.exceptions import InvalidGitCredentialTypeError
from app.v1.kits.application.interfaces.repository_repository import RepositoryRepository
from app.v1.kits.domain.entities.repository import Repository
from app.v1.kits.domain.events.repository_registered import RepositoryRegistered
from app.v1.kits.domain.value_objects.sync_status import SyncStatus
from app.v1.servers.application.interfaces.credential_repository import CredentialRepository
from app.v1.shared.application.interfaces.event_bus import EventBus

_GIT_CREDENTIAL_TYPES = {"git_https", "git_ssh"}


class RegisterRepository:
    """Use Case para registrar y persistir un nuevo repositorio Git."""

    def __init__(
        self,
        repository_repository: RepositoryRepository | None = None,
        credential_repository: CredentialRepository | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._repository_repo = repository_repository
        self._credential_repo = credential_repository
        self._event_bus = event_bus

    async def execute(
        self,
        user_id: str,
        url: str,
        ref: str,
        correlation_id: str,
        credential_id: Optional[str] = None,
    ) -> RepositoryResult:
        """Registra un nuevo repositorio Git como fuente de kits.

        Args:
            user_id: ID del usuario propietario
            url: URL del repositorio Git
            ref: Rama, tag o commit SHA de referencia
            correlation_id: ID de trazabilidad del request
            credential_id: ID opcional de la credencial Git (solo git_https o git_ssh)

        Returns:
            RepositoryResult con los datos del repositorio creado

        Raises:
            InvalidGitCredentialTypeError: Si la credencial no es de tipo git_https o git_ssh (RN-23)
        """
        if credential_id is not None and self._credential_repo is not None:
            credential = await self._credential_repo.find_by_id(credential_id, user_id)
            if credential is not None and credential.type.value not in _GIT_CREDENTIAL_TYPES:
                raise InvalidGitCredentialTypeError()

        now = datetime.now(timezone.utc)

        repository = Repository(
            id=str(uuid4()),
            user_id=user_id,
            url=url,
            ref=ref,
            credential_id=credential_id,
            sync_status=SyncStatus("never_synced"),
            last_synced_at=None,
            last_commit_sha=None,
            sync_error_message=None,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )

        if self._repository_repo is not None:
            await self._repository_repo.save(repository)

        if self._event_bus is not None:
            await self._event_bus.publish(
                RepositoryRegistered(
                    repository_id=repository.id,
                    user_id=user_id,
                    url=url,
                    ref=ref,
                    correlation_id=correlation_id,
                )
            )

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
