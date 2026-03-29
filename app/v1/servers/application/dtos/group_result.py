"""DTO para resultado de operaciones sobre grupos de servidores."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class GroupResult:
    """Resultado de crear o actualizar un grupo de servidores."""

    group_id: str
    user_id: str
    name: str
    description: str | None
    server_ids: list[str]
    created_at: datetime
    updated_at: datetime
