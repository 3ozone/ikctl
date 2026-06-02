"""Port KitRepository (cross-module, read-only) — T-09.3.

Port propio del módulo pipelines para validar que los kits del pipeline
son usables antes de lanzar una ejecución.
El adapter en main.py delega al SQLAlchemyKitRepository del módulo kits.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.v1.kits.domain.entities.kit import Kit


class KitRepository(ABC):
    """Contrato de solo lectura sobre kits (uso interno de LaunchPipeline)."""

    @abstractmethod
    async def find_by_id_internal(self, kit_id: str) -> Optional[Kit]:
        """Devuelve el kit por id sin validar ownership, o None si no existe."""
