"""Evento de dominio: OperationCancelled."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.shared.domain.events import DomainEvent


class OperationCancelled(DomainEvent):
    """Evento publicado cuando una operación es cancelada."""

    def __init__(
        self,
        operation_id: str,
        user_id: str,
        was_unsafe: bool,
        correlation_id: str,
    ) -> None:
        super().__init__(
            event_id=str(uuid4()),
            correlation_id=correlation_id,
            event_type="OperationCancelled",
            aggregate_id=operation_id,
            aggregate_type="Operation",
            payload={
                "operation_id": operation_id,
                "user_id": user_id,
                "was_unsafe": was_unsafe,
            },
            version=1,
            occurred_at=datetime.now(timezone.utc),
        )
