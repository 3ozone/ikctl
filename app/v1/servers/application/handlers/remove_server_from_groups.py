"""Handler: elimina un servidor de todos los grupos cuando el servidor es eliminado."""
from app.v1.shared.application.interfaces.event_bus import EventHandler
from app.v1.shared.domain.events import DomainEvent
from app.v1.servers.application.interfaces.group_repository import GroupRepository


class RemoveServerFromGroupsOnServerDeleted(EventHandler):
    """
    Escucha el evento ServerDeleted y elimina el server_id de todos los
    grupos del usuario que lo contenían.

    Garantiza consistencia interna del módulo: un servidor eliminado
    no puede quedar referenciado en ningún grupo.

    Es idempotente: si el servidor ya no está en ningún grupo, no hace nada.
    """

    def __init__(self, group_repository: GroupRepository) -> None:
        self._group_repo = group_repository

    async def handle(self, event: DomainEvent) -> None:
        """
        Procesa el evento ServerDeleted.

        Args:
            event: Evento de dominio con payload {"server_id": str, "user_id": str}
        """
        server_id: str = event.payload["server_id"]
        user_id: str = event.payload["user_id"]

        groups = await self._group_repo.find_all_by_user(user_id=user_id, page=1, per_page=1000)

        for group in groups:
            if server_id in group.server_ids:
                group.remove_server(server_id)
                await self._group_repo.update(group)
