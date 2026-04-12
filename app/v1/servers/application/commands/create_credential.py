"""Use Case para crear una nueva credencial."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.value_objects.credential_type import CredentialType
from app.v1.servers.application.dtos.credential_result import CredentialResult
from app.v1.servers.application.interfaces.credential_repository import CredentialRepository
from app.v1.servers.domain.events.credential_created import CredentialCreated
from app.v1.shared.application.interfaces.event_bus import EventBus


class CreateCredential:
    """Use Case para crear y persistir una nueva credencial de acceso."""

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
        name: str,
        credential_type: str,
        username: str | None,
        password: str | None,
        private_key: str | None,
        correlation_id: str,
    ) -> CredentialResult:
        """Crea una nueva credencial.

        Args:
            user_id: ID del usuario propietario
            name: Nombre descriptivo de la credencial
            credential_type: Tipo ("ssh", "git_https", "git_ssh")
            username: Usuario para autenticación (requerido en ssh y git_https)
            password: Contraseña (requerida en ssh sin private_key, y git_https)
            private_key: Clave privada SSH (requerida en git_ssh, opcional en ssh)
            correlation_id: ID de trazabilidad del request

        Returns:
            CredentialResult sin password ni private_key

        Raises:
            InvalidCredentialTypeError: Si el tipo no es válido
            InvalidCredentialConfigurationError: Si la combinación de campos no es válida
        """
        now = datetime.now(timezone.utc)

        credential = Credential(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            type=CredentialType(credential_type),
            username=username,
            password=password,
            private_key=private_key,
            created_at=now,
            updated_at=now,
        )
        credential.validate()

        if self._repo is not None:
            await self._repo.save(credential)

        if self._event_bus is not None:
            await self._event_bus.publish(
                CredentialCreated(
                    credential_id=credential.id,
                    user_id=user_id,
                    name=name,
                    credential_type=credential_type,
                    correlation_id=correlation_id,
                )
            )

        return CredentialResult(
            credential_id=credential.id,
            user_id=credential.user_id,
            name=credential.name,
            credential_type=credential.type.value,
            username=credential.username,
            has_private_key=credential.private_key is not None,
            created_at=credential.created_at,
            updated_at=credential.updated_at,
        )
