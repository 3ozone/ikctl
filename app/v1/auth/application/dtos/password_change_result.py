"""
DTO para resultado de cambio de contraseña.

Usado por ChangePassword use case.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordChangeResult:
    """Resultado de un cambio de contraseña."""

    success: bool
    user_id: str
    revoked_sessions_count: int = 0
