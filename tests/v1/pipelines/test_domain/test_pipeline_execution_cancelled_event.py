"""Tests para el evento de dominio PipelineExecutionCancelled (R4)."""
from uuid import uuid4

from app.v1.pipelines.domain.events.pipeline_execution_cancelled import (
    PipelineExecutionCancelled,
)


class TestPipelineExecutionCancelledCreation:
    """Creación del evento PipelineExecutionCancelled (R4)."""

    def test_event_creation(self):
        corr_id = str(uuid4())
        event = PipelineExecutionCancelled(
            execution_id="exec-001",
            pipeline_id="pipe-001",
            user_id="user-001",
            correlation_id=corr_id,
        )
        assert event.aggregate_id == "exec-001"
        assert event.aggregate_type == "PipelineExecution"
        assert event.event_type == "PipelineExecutionCancelled"
        assert event.payload["execution_id"] == "exec-001"
        assert event.payload["pipeline_id"] == "pipe-001"
        assert event.payload["user_id"] == "user-001"

    def test_event_serialization(self):
        corr_id = str(uuid4())
        event = PipelineExecutionCancelled(
            execution_id="exec-001",
            pipeline_id="pipe-001",
            user_id="user-001",
            correlation_id=corr_id,
        )
        d = event.to_dict()
        assert d["event_type"] == "PipelineExecutionCancelled"
        assert d["aggregate_id"] == "exec-001"
        assert d["payload"]["execution_id"] == "exec-001"