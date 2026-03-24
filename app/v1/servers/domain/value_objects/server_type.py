"""Value Object ServerType."""
from dataclasses import dataclass

from app.v1.servers.domain.exceptions.server import InvalidServerTypeError

VALID_TYPES = {"remote", "local"}


@dataclass(frozen=True)
class ServerType:
    """Tipo de servidor. Valores permitidos: remote, local."""

    value: str

    def __post_init__(self) -> None:
        if self.value not in VALID_TYPES:
            raise InvalidServerTypeError()
