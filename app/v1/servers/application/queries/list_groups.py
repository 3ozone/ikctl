"""Use Case para listar grupos de un usuario con paginación."""
from app.v1.servers.application.dtos.group_list_result import GroupListResult
from app.v1.servers.application.dtos.group_result import GroupResult
from app.v1.servers.application.interfaces.group_repository import GroupRepository


class ListGroups:
    """Use Case para listar grupos de un usuario paginados."""

    def __init__(
        self,
        group_repository: GroupRepository | None = None,
    ) -> None:
        self._group_repo = group_repository

    async def execute(
        self,
        user_id: str,
        page: int,
        per_page: int,
    ) -> GroupListResult:
        """Lista los grupos del usuario con paginación.

        Args:
            user_id: ID del usuario propietario
            page: Número de página (1-based)
            per_page: Elementos por página

        Returns:
            GroupListResult paginado
        """
        groups = []
        if self._group_repo is not None:
            groups = await self._group_repo.find_all_by_user(user_id, page, per_page)

        items = [
            GroupResult(
                group_id=g.id,
                user_id=g.user_id,
                name=g.name,
                description=g.description,
                server_ids=g.server_ids,
                created_at=g.created_at,
                updated_at=g.updated_at,
            )
            for g in groups
        ]

        return GroupListResult(
            items=items,
            total=len(items),
            page=page,
            per_page=per_page,
        )
