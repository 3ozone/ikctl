"""DTO para resultado de listar grupos paginados."""
from dataclasses import dataclass

from app.v1.servers.application.dtos.group_result import GroupResult


@dataclass(frozen=True)
class GroupListResult:
    """Resultado paginado de listar grupos de un usuario."""

    items: list[GroupResult]
    total: int
    page: int
    per_page: int
