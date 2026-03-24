"""Use Case para actualizar una credencial existente."""
from datetime import datetime, timezone

from app.v1.servers.application.dtos.credential_result import CredentialResult
from app.v1.servers.application.interfaces.credential_repository import CredentialRepository
from app.v1.servers.domain.exceptions.credential import CredentialNotFoundError
from app.v1.servers.domain.events.credential_updated import CredentialUpdated
from app.v1.shared.application.interfaces.event_bus import EventBus


class UpdateCredential:
    """Use Case para actualizar los campos de una credencial existente."""

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
        name: str,
        username: str | None,
        password: str | None,
        private_key: str | None,
        correlation_id: str,
    ) -> CredentialResult:
        """Actualiza una credencial existente del usuario.

        Args:
            user_id: ID del usuario propietario
            credential_id: ID de la credencial a actualizar
            name: Nuevo nombre descriptivo
            username: Nuevo usuario de autenticación
            password: Nueva contraseña
            private_key: Nueva clave privada SSH
            correlation_id: ID de trazabilidad del request

        Returns:
            CredentialResult sin password ni private_key

        Raises:
            CredentialNotFoundError: Si la credencial no existe o no pertenece al usuario
        """
        if self._repo is not None:
            credential = await self._repo.find_by_id(credential_id, user_id)
            if credential is None:
                raise CredentialNotFoundError()
        else:
            raise CredentialNotFoundError()

        now = datetime.now(timezone.utc)
        credential.update(
            name=name,
            username=username,
            password=password,
            private_key=private_key,
            updated_at=now,
        )

        await self._repo.update(credential)

        if self._event_bus is not None:
            await self._event_bus.publish(
                CredentialUpdated(
                    credential_id=credential.id,
                    user_id=user_id,
                    correlation_id=correlation_id,
                )
            )

        return CredentialResult(
            credential_id=credential.id,
            user_id=credential.user_id,
            name=credential.name,
            credential_type=credential.type.value,
            username=credential.username,
            created_at=credential.created_at,
            updated_at=credential.updated_at,
        )
