"""Evento de dominio: OperationLaunched."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.shared.domain.events import DomainEvent


class OperationLaunched(DomainEvent):
    """Evento publicado cuando se lanza una nueva operación."""

    def __init__(
        self,
        operation_id: str,
        server_id: str,
        kit_id: str,
        user_id: str,
        correlation_id: str,
    ) -> None:
        super().__init__(
            event_id=str(uuid4()),
            correlation_id=correlation_id,
            event_type="OperationLaunched",
            aggregate_id=operation_id,
            aggregate_type="Operation",
            payload={
                "operation_id": operation_id,
                "server_id": server_id,
                "kit_id": kit_id,
                "user_id": user_id,
            },
            version=1,
            occurred_at=datetime.now(timezone.utc),
        )
