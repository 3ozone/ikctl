"""Use Case para listar credenciales de un usuario con paginación."""
from app.v1.servers.application.dtos.credential_list_result import CredentialListResult
from app.v1.servers.application.dtos.credential_result import CredentialResult
from app.v1.servers.application.interfaces.credential_repository import CredentialRepository


class ListCredentials:
    """Use Case para listar credenciales de un usuario paginadas."""

    def __init__(
        self,
        credential_repository: CredentialRepository | None = None,
    ) -> None:
        self._credential_repo = credential_repository

    async def execute(
        self,
        user_id: str,
        page: int,
        per_page: int,
    ) -> CredentialListResult:
        """Lista las credenciales del usuario con paginación.

        Args:
            user_id: ID del usuario propietario
            page: Número de página (1-based)
            per_page: Elementos por página

        Returns:
            CredentialListResult paginado sin password ni private_key
        """
        credentials = []
        if self._credential_repo is not None:
            credentials = await self._credential_repo.find_all_by_user(user_id, page, per_page)

        items = [
            CredentialResult(
                credential_id=c.id,
                user_id=c.user_id,
                name=c.name,
                credential_type=c.type.value,
                username=c.username,
                has_private_key=c.private_key is not None,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in credentials
        ]

        return CredentialListResult(
            items=items,
            total=len(items),
            page=page,
            per_page=per_page,
        )
