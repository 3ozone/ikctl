"""Port KitRepository (cross-module) — T-08.

Port propio del módulo operations para acceder a kits sin filtro de
ownership. El adapter en main.py delega al SQLAlchemyKitRepository de kits.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.v1.kits.domain.entities.kit import Kit


class KitRepository(ABC):
    """Contrato de solo lectura sobre kits (uso interno de tasks)."""

    @abstractmethod
    async def find_by_id_internal(self, kit_id: str) -> Optional[Kit]:
        """Devuelve el kit por id sin validar ownership, o None si no existe."""
