"""
DTO para perfil de usuario.

Usado por GetUserProfile use case y endpoints de presentación.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class UserProfile:
    """Perfil público de usuario (sin datos sensibles)."""

    id: str
    name: str
    email: str
    is_verified: bool
    is_2fa_enabled: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
