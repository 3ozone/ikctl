"""
DTO para resultado de verificación.

Usado por VerifyEmail, ResetPassword use cases.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationResult:
    """Resultado de una verificación (email, password reset)."""

    success: bool
    user_id: str
    message: str = ""
