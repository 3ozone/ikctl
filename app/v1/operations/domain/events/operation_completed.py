"""Evento de dominio: OperationCompleted."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.shared.domain.events import DomainEvent


class OperationCompleted(DomainEvent):
    """Evento publicado cuando una operación finaliza con éxito."""

    def __init__(
        self,
        operation_id: str,
        user_id: str,
        duration_ms: int,
        correlation_id: str,
    ) -> None:
        super().__init__(
            event_id=str(uuid4()),
            correlation_id=correlation_id,
            event_type="OperationCompleted",
            aggregate_id=operation_id,
            aggregate_type="Operation",
            payload={
                "operation_id": operation_id,
                "user_id": user_id,
                "duration_ms": duration_ms,
            },
            version=1,
            occurred_at=datetime.now(timezone.utc),
        )
