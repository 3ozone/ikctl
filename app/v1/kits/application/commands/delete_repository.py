"""Use Case para eliminar un repositorio Git y todos sus kits."""
from app.v1.kits.application.exceptions import (
    RepositoryInUseError,
    RepositoryNotFoundError,
)
from app.v1.kits.application.interfaces.repository_repository import RepositoryRepository
from app.v1.kits.domain.events.repository_deleted import RepositoryDeleted
from app.v1.shared.application.interfaces.event_bus import EventBus


class DeleteRepository:
    """Use Case para eliminar físicamente un repositorio Git y todos sus kits.

    Valida ownership y que no haya kits con referencias activas antes de borrar.
    """

    def __init__(
        self,
        repository_repository: RepositoryRepository | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._repository_repo = repository_repository
        self._event_bus = event_bus

    async def execute(
        self,
        user_id: str,
        repository_id: str,
        correlation_id: str,
    ) -> None:
        """Elimina físicamente un repositorio y todos sus kits.

        Args:
            user_id: ID del usuario propietario
            repository_id: ID del repositorio a eliminar
            correlation_id: ID de trazabilidad del request

        Raises:
            RepositoryNotFoundError: Si el repositorio no existe o no pertenece al usuario (RN-01)
            RepositoryInUseError: Si algún kit del repositorio tiene referencias activas (RN-30)
        """
        repository = await self._repository_repo.find_by_id(repository_id, user_id)
        if repository is None:
            raise RepositoryNotFoundError()

        has_references = await self._repository_repo.has_kits_with_references(repository_id)
        if has_references:
            raise RepositoryInUseError()

        await self._repository_repo.delete(repository_id)

        if self._event_bus is not None:
            await self._event_bus.publish(
                RepositoryDeleted(
                    repository_id=repository_id,
                    user_id=user_id,
                    correlation_id=correlation_id,
                )
            )
