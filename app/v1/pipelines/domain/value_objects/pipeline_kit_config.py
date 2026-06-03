"""Value Object PipelineKitConfig — configuración de un kit dentro de un pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.v1.pipelines.domain.exceptions.pipeline_kit_config import InvalidPipelineKitConfigError

_VALID_DEBUG_LEVELS = frozenset({"none", "errors", "full"})


@dataclass(frozen=True)
class PipelineKitConfig:
    """Configuración de un kit dentro de un pipeline.

    Atributos:
        kit_id: ID del kit a ejecutar (obligatorio).
        sudo: Si ejecutar con sudo. None = heredar del pipeline.
        debug_level: Nivel de debug. None = heredar del pipeline.
        values: Variables de plantilla específicas de este kit.
    """

    kit_id: str
    sudo: Optional[bool] = None
    debug_level: Optional[str] = None
    values: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.kit_id or not self.kit_id.strip():
            raise InvalidPipelineKitConfigError(
                f"kit_id no puede estar vacío: '{self.kit_id}'"
            )
        if self.debug_level is not None and self.debug_level not in _VALID_DEBUG_LEVELS:
            raise InvalidPipelineKitConfigError(
                f"debug_level inválido: '{self.debug_level}'. "
                f"Valores válidos: {sorted(_VALID_DEBUG_LEVELS)}"
            )

    def __hash__(self) -> int:
        return hash((self.kit_id, self.sudo, self.debug_level, tuple(sorted(self.values.items()))))