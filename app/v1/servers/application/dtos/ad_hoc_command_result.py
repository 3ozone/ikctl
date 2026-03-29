"""DTO para resultado de ejecutar un comando ad-hoc en un servidor."""
from dataclasses import dataclass


@dataclass(frozen=True)
class AdHocCommandResult:
    """Resultado de ejecutar un comando ad-hoc en un servidor."""

    server_id: str
    command: str
    stdout: str
    stderr: str
    exit_code: int
