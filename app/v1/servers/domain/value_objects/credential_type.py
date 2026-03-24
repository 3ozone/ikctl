"""Value Object CredentialType."""
from dataclasses import dataclass

from app.v1.servers.domain.exceptions.credential import InvalidCredentialTypeError

VALID_TYPES = {"ssh", "git_https", "git_ssh"}


@dataclass(frozen=True)
class CredentialType:
    """Tipo de credencial. Valores permitidos: ssh, git_https, git_ssh."""

    value: str

    def __post_init__(self) -> None:
        if self.value not in VALID_TYPES:
            raise InvalidCredentialTypeError()
