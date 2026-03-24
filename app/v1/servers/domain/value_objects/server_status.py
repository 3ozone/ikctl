"""Value Object ServerStatus."""
from dataclasses import dataclass

from app.v1.servers.domain.exceptions.server import InvalidServerStatusError

VALID_STATUSES = {"active", "inactive"}


@dataclass(frozen=True)
class ServerStatus:
    """Estado de servidor. Valores permitidos: active, inactive."""

    value: str

    def __post_init__(self) -> None:
        if self.value not in VALID_STATUSES:
            raise InvalidServerStatusError()
