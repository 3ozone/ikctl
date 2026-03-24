"""Evento de dominio: ServerDeleted."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.shared.domain.events import DomainEvent


class ServerDeleted(DomainEvent):
    """Evento que se publica cuando se elimina un servidor.

    Permite a otros módulos reaccionar, por ejemplo eliminando
    el servidor de todos los grupos que lo contenían.
    """

    def __init__(self, server_id: str, user_id: str, correlation_id: str) -> None:
        super().__init__(
            event_id=str(uuid4()),
            correlation_id=correlation_id,
            event_type="ServerDeleted",
            aggregate_id=server_id,
            aggregate_type="Server",
            payload={
                "server_id": server_id,
                "user_id": user_id,
            },
            version=1,
            occurred_at=datetime.now(timezone.utc),
        )
