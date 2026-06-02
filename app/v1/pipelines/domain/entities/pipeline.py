"""Entity Pipeline — definición reutilizable (template) de un pipeline de kits × servidores."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget


@dataclass
class Pipeline:
    """Definición reutilizable que combina kits con servidores target.

    RN-14: sudo por kit prioridad sobre global.
    RN-15: debug_level por kit prioridad sobre global.
    RN-17: servidor local no permitido en targets.
    """

    id: str
    user_id: str
    name: str
    targets: list[PipelineTarget]
    kits: list[PipelineKitConfig]
    sudo: bool = False
    debug_level: str = "none"
    values: dict = field(default_factory=dict)
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def update(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        targets: Optional[list[PipelineTarget]] = None,
        kits: Optional[list[PipelineKitConfig]] = None,
        values: Optional[dict] = None,
        sudo: Optional[bool] = None,
        debug_level: Optional[str] = None,
    ) -> None:
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if targets is not None:
            self.targets = targets
        if kits is not None:
            self.kits = kits
        if values is not None:
            self.values = values
        if sudo is not None:
            self.sudo = sudo
        if debug_level is not None:
            self.debug_level = debug_level

    def resolved_sudo_for(self, kit_id: str) -> bool:
        """RN-14: sudo por kit prioridad sobre global. Si kit no especifica, hereda global."""
        for kit_config in self.kits:
            if kit_config.kit_id == kit_id and kit_config.sudo is not None:
                return kit_config.sudo
        return self.sudo

    def resolved_debug_level_for(self, kit_id: str) -> str:
        """RN-15: debug_level por kit prioridad sobre global. Si kit no especifica, hereda global."""
        for kit_config in self.kits:
            if kit_config.kit_id == kit_id and kit_config.debug_level is not None:
                return kit_config.debug_level
        return self.debug_level

    def has_local_server(self, local_server_ids: list[str]) -> bool:
        """RN-17: devuelve True si algún target es un servidor local."""
        local_set = set(local_server_ids)
        return any(t.server_id in local_set for t in self.targets)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pipeline):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)