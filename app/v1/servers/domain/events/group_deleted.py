"""Evento de dominio: GroupDeleted."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.shared.domain.events import DomainEvent


class GroupDeleted(DomainEvent):
    """Evento que se publica cuando se elimina un grupo de servidores."""

    def __init__(self, group_id: str, user_id: str, correlation_id: str) -> None:
        super().__init__(
            event_id=str(uuid4()),
            correlation_id=correlation_id,
            event_type="GroupDeleted",
            aggregate_id=group_id,
            aggregate_type="Group",
            payload={
                "group_id": group_id,
                "user_id": user_id,
            },
            version=1,
            occurred_at=datetime.now(timezone.utc),
        )
