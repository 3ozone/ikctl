"""Value Object PipelineTarget — referencia a un servidor destino dentro de un pipeline."""
from __future__ import annotations

from dataclasses import dataclass

from app.v1.pipelines.domain.exceptions.pipeline_target import InvalidPipelineTargetError


@dataclass(frozen=True)
class PipelineTarget:
    """Referencia inmutable a un servidor destino dentro de un pipeline.

    Igualdad por valor: dos PipelineTarget con el mismo server_id son iguales.
    """

    server_id: str

    def __post_init__(self) -> None:
        if not self.server_id or not self.server_id.strip():
            raise InvalidPipelineTargetError(
                f"server_id no puede estar vacío: '{self.server_id}'"
            )