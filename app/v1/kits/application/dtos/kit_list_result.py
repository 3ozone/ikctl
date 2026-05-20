"""DTO para resultado de listar kits paginados."""
from dataclasses import dataclass

from app.v1.kits.application.dtos.kit_result import KitResult


@dataclass(frozen=True)
class KitListResult:
    """Resultado paginado de listar kits de un usuario."""

    items: list[KitResult]
    total: int
    page: int
    per_page: int
