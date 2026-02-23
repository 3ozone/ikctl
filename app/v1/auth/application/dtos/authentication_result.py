"""
DTO para el resultado de autenticación.

Usado por AuthenticateUser, AuthenticateWithGitHub use cases.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthenticationResult:
    """Resultado de una autenticación exitosa."""

    user_id: str
    access_token: str
    refresh_token: str
    requires_2fa: bool = False
