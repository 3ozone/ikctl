"""Excepciones del dominio de autenticación."""
from .email import InvalidEmailError
from .password import InvalidPasswordError
from .user import InvalidUserError, UserNotFoundError, UserAlreadyExistsError
from .token import (
    InvalidJWTTokenError,
    InvalidRefreshTokenError,
    InvalidVerificationTokenError,
    InvalidPasswordHistoryError,
)

__all__ = [
    "InvalidEmailError",
    "InvalidPasswordError",
    "InvalidUserError",
    "UserNotFoundError",
    "UserAlreadyExistsError",
    "InvalidJWTTokenError",
    "InvalidRefreshTokenError",
    "InvalidVerificationTokenError",
    "InvalidPasswordHistoryError",
]
