"""Use Case para eliminar una credencial."""
from app.v1.servers.application.interfaces.credential_repository import CredentialRepository
from app.v1.servers.domain.exceptions.credential import CredentialNotFoundError, CredentialInUseError
from app.v1.servers.domain.events.credential_deleted import CredentialDeleted
from app.v1.shared.application.interfaces.event_bus import EventBus


class DeleteCredential:
    """Use Case para eliminar una credencial de acceso.

    Valida ownership (RN-01) y que no esté en uso por ningún servidor (RN-06).
    """

    def __init__(
        self,
        credential_repository: CredentialRepository | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._repo = credential_repository
        self._event_bus = event_bus

    async def execute(
        self,
        user_id: str,
        credential_id: str,
        correlation_id: str,
    ) -> None:
        """Elimina una credencial del usuario.

        Args:
            user_id: ID del usuario propietario
            credential_id: ID de la credencial a eliminar
            correlation_id: ID de trazabilidad del request

        Raises:
            CredentialNotFoundError: Si la credencial no existe o no pertenece al usuario
            CredentialInUseError: Si la credencial está siendo usada por algún servidor (RN-06)
        """
        if self._repo is None:
            raise CredentialNotFoundError()

        credential = await self._repo.find_by_id(credential_id, user_id)
        if credential is None:
            raise CredentialNotFoundError()

        in_use = await self._repo.is_used_by_server(credential_id)
        if in_use:
            raise CredentialInUseError()

        await self._repo.delete(credential_id)

        if self._event_bus is not None:
            await self._event_bus.publish(
                CredentialDeleted(
                    credential_id=credential_id,
                    user_id=user_id,
                    correlation_id=correlation_id,
                )
            )
