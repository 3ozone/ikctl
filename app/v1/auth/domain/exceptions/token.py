"""Excepciones de dominio para tokens (JWT, Refresh, Verification, PasswordHistory)."""
from app.v1.shared.domain.exceptions import DomainException


class InvalidJWTTokenError(DomainException):
    """Error cuando el JWT Token es inválido."""


class InvalidRefreshTokenError(DomainException):
    """Error cuando el RefreshToken es inválido."""


class InvalidVerificationTokenError(DomainException):
    """Error cuando el VerificationToken es inválido."""


class InvalidPasswordHistoryError(DomainException):
    """Error cuando el PasswordHistory es inválido."""
