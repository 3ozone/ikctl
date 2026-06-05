"""Value Object PipelineTarget — referencia a un servidor destino dentro de un pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.v1.pipelines.domain.exceptions.pipeline_target import InvalidPipelineTargetError


@dataclass(frozen=True)
class PipelineTarget:
    """Referencia inmutable a un servidor destino dentro de un pipeline.

    Igualdad por valor: dos PipelineTarget con el mismo server_id son iguales.

    kit_ids:
        Tupla de IDs de kits a ejecutar en este target.
        None = ejecutar todos los kits globales del pipeline.
    values:
        Variables de plantilla específicas de este target.
        Se mergean con pipeline.values y kit.values (kit > target > global).
    """

    server_id: str
    kit_ids: Optional[tuple[str, ...]] = None
    values: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.server_id or not self.server_id.strip():
            raise InvalidPipelineTargetError(
                f"server_id no puede estar vacío: '{self.server_id}'"
            )
        if self.kit_ids is not None:
            for kid in self.kit_ids:
                if not kid or not kid.strip():
                    raise InvalidPipelineTargetError(
                        f"kit_id en kit_ids no puede estar vacío: '{kid}'"
                    )

    def __hash__(self) -> int:
        return hash((self.server_id, self.kit_ids, tuple(sorted(self.values.items()))))