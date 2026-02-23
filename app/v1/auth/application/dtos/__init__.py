"""
Data Transfer Objects (DTOs).

Objetos simples para transferir datos entre capas sin lógica de negocio.
"""

from .authentication_result import AuthenticationResult
from .token_pair import TokenPair
from .user_profile import UserProfile
from .verification_result import VerificationResult
from .totp_setup import TOTPSetup
from .password_change_result import PasswordChangeResult
from .registration_result import RegistrationResult

__all__ = [
    "AuthenticationResult",
    "TokenPair",
    "UserProfile",
    "VerificationResult",
    "TOTPSetup",
    "PasswordChangeResult",
    "RegistrationResult",
]
