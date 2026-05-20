"""DTO para resultado de listar repositorios paginados."""
from dataclasses import dataclass

from app.v1.kits.application.dtos.repository_result import RepositoryResult


@dataclass(frozen=True)
class RepositoryListResult:
    """Resultado paginado de listar repositorios de un usuario."""

    items: list[RepositoryResult]
    total: int
    page: int
    per_page: int
