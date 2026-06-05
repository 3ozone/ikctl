"""Evento de dominio: PipelineExecutionCancelled."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.shared.domain.events import DomainEvent


class PipelineExecutionCancelled(DomainEvent):
    """Evento publicado cuando se cancela una ejecución de pipeline."""

    def __init__(
        self,
        execution_id: str,
        pipeline_id: str,
        user_id: str,
        correlation_id: str,
    ) -> None:
        super().__init__(
            event_id=str(uuid4()),
            correlation_id=correlation_id,
            event_type="PipelineExecutionCancelled",
            aggregate_id=execution_id,
            aggregate_type="PipelineExecution",
            payload={
                "execution_id": execution_id,
                "pipeline_id": pipeline_id,
                "user_id": user_id,
            },
            version=1,
            occurred_at=datetime.now(timezone.utc),
        )