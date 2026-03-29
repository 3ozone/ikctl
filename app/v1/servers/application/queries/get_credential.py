"""Use Case para obtener una credencial por su ID."""
from app.v1.servers.application.dtos.credential_result import CredentialResult
from app.v1.servers.application.interfaces.credential_repository import CredentialRepository
from app.v1.servers.domain.exceptions.credential import CredentialNotFoundError


class GetCredential:
    """Use Case para obtener una credencial del usuario.

    Valida ownership (RN-01) y devuelve el DTO sin datos sensibles.
    """

    def __init__(
        self,
        credential_repository: CredentialRepository | None = None,
    ) -> None:
        self._credential_repo = credential_repository

    async def execute(
        self,
        user_id: str,
        credential_id: str,
    ) -> CredentialResult:
        """Obtiene una credencial por su ID.

        Args:
            user_id: ID del usuario propietario
            credential_id: ID de la credencial a obtener

        Returns:
            CredentialResult sin password ni private_key

        Raises:
            CredentialNotFoundError: Si la credencial no existe o no pertenece al usuario (RN-01)
        """
        credential = None
        if self._credential_repo is not None:
            credential = await self._credential_repo.find_by_id(credential_id, user_id)

        if credential is None:
            raise CredentialNotFoundError()

        return CredentialResult(
            credential_id=credential.id,
            user_id=credential.user_id,
            name=credential.name,
            credential_type=credential.type.value,
            username=credential.username,
            created_at=credential.created_at,
            updated_at=credential.updated_at,
        )
