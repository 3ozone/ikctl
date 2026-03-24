"""Evento de dominio: ServerRegistered."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.shared.domain.events import DomainEvent


class ServerRegistered(DomainEvent):
    """Evento que se publica cuando se registra un nuevo servidor."""

    def __init__(self, server_id: str, user_id: str, name: str, server_type: str, correlation_id: str) -> None:
        super().__init__(
            event_id=str(uuid4()),
            correlation_id=correlation_id,
            event_type="ServerRegistered",
            aggregate_id=server_id,
            aggregate_type="Server",
            payload={
                "server_id": server_id,
                "user_id": user_id,
                "name": name,
                "server_type": server_type,
            },
            version=1,
            occurred_at=datetime.now(timezone.utc),
        )
