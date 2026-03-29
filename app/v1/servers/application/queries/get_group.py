"""Use Case para obtener un grupo por su ID."""
from app.v1.servers.application.dtos.group_result import GroupResult
from app.v1.servers.application.interfaces.group_repository import GroupRepository
from app.v1.servers.domain.exceptions.group import GroupNotFoundError


class GetGroup:
    """Use Case para obtener un grupo del usuario.

    Valida ownership (RN-01) y devuelve el DTO con la lista de servidores.
    """

    def __init__(
        self,
        group_repository: GroupRepository | None = None,
    ) -> None:
        self._group_repo = group_repository

    async def execute(
        self,
        user_id: str,
        group_id: str,
    ) -> GroupResult:
        """Obtiene un grupo por su ID.

        Args:
            user_id: ID del usuario propietario
            group_id: ID del grupo a obtener

        Returns:
            GroupResult con la lista de servidores del grupo

        Raises:
            GroupNotFoundError: Si el grupo no existe o no pertenece al usuario (RN-01)
        """
        group = None
        if self._group_repo is not None:
            group = await self._group_repo.find_by_id(group_id, user_id)

        if group is None:
            raise GroupNotFoundError()

        return GroupResult(
            group_id=group.id,
            user_id=group.user_id,
            name=group.name,
            description=group.description,
            server_ids=group.server_ids,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )
