"""
DTO para par de tokens (access + refresh).

Usado por CreateTokens, RefreshAccessToken use cases.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TokenPair:
    """Par de tokens JWT (access + refresh)."""

    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    token_type: str = "Bearer"
