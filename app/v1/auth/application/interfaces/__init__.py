"""
Interfaces (Ports) - Contratos para adaptadores externos.

Define abstracciones (ABC) que serán implementadas en infrastructure/.
Dependency Inversion: application/ define interfaces, infrastructure/ las implementa.
"""

from .user_repository import UserRepository
from .refresh_token_repository import RefreshTokenRepository
from .verification_token_repository import VerificationTokenRepository
from .password_history_repository import PasswordHistoryRepository
from .email_service import EmailService
from .jwt_provider import JWTProvider
from .totp_provider import TOTPProvider
from .github_oauth import IGitHubOAuth

__all__ = [
    "UserRepository",
    "RefreshTokenRepository",
    "VerificationTokenRepository",
    "PasswordHistoryRepository",
    "EmailService",
    "JWTProvider",
    "TOTPProvider",
    "IGitHubOAuth",
]
