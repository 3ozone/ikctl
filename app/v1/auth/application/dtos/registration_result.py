"""
DTO para resultado de registro.

Usado por RegisterUser use case.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RegistrationResult:
    """Resultado de un registro de usuario."""

    user_id: str
    email: str
    verification_token_sent: bool
