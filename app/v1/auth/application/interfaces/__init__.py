"""
Interfaces (Ports) - Contratos para adaptadores externos.

Define abstracciones (ABC) que serán implementadas en infrastructure/.
Dependency Inversion: application/ define interfaces, infrastructure/ las implementa.
"""

from .user_repository import IUserRepository
from .refresh_token_repository import IRefreshTokenRepository
from .verification_token_repository import IVerificationTokenRepository
from .password_history_repository import IPasswordHistoryRepository
from .email_service import IEmailService
from .jwt_provider import IJWTProvider
from .totp_provider import ITOTPProvider
from .github_oauth import IGitHubOAuth

__all__ = [
    "IUserRepository",
    "IRefreshTokenRepository",
    "IVerificationTokenRepository",
    "IPasswordHistoryRepository",
    "IEmailService",
    "IJWTProvider",
    "ITOTPProvider",
    "IGitHubOAuth",
]
