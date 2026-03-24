"""Evento de dominio: ServerStatusChanged."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.shared.domain.events import DomainEvent


class ServerStatusChanged(DomainEvent):
    """Evento que se publica cuando cambia el estado de un servidor (active/inactive)."""

    def __init__(self, server_id: str, user_id: str, new_status: str, correlation_id: str) -> None:
        super().__init__(
            event_id=str(uuid4()),
            correlation_id=correlation_id,
            event_type="ServerStatusChanged",
            aggregate_id=server_id,
            aggregate_type="Server",
            payload={
                "server_id": server_id,
                "user_id": user_id,
                "new_status": new_status,
            },
            version=1,
            occurred_at=datetime.now(timezone.utc),
        )
