"""DTO para resultado de listar servidores paginados."""
from dataclasses import dataclass

from app.v1.servers.application.dtos.server_result import ServerResult


@dataclass(frozen=True)
class ServerListResult:
    """Resultado paginado de listar servidores de un usuario."""

    items: list[ServerResult]
    total: int
    page: int
    per_page: int
