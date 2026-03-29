"""DTO para resultado de listar credenciales paginadas."""
from dataclasses import dataclass

from app.v1.servers.application.dtos.credential_result import CredentialResult


@dataclass(frozen=True)
class CredentialListResult:
    """Resultado paginado de listar credenciales de un usuario."""

    items: list[CredentialResult]
    total: int
    page: int
    per_page: int
