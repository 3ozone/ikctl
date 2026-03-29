"""Evento de dominio: GroupUpdated."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.shared.domain.events import DomainEvent


class GroupUpdated(DomainEvent):
    """Evento que se publica cuando se actualiza la configuración de un grupo existente."""

    def __init__(self, group_id: str, user_id: str, name: str, correlation_id: str) -> None:
        super().__init__(
            event_id=str(uuid4()),
            correlation_id=correlation_id,
            event_type="GroupUpdated",
            aggregate_id=group_id,
            aggregate_type="Group",
            payload={
                "group_id": group_id,
                "user_id": user_id,
                "name": name,
            },
            version=1,
            occurred_at=datetime.now(timezone.utc),
        )
