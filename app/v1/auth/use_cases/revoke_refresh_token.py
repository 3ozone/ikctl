"""Use Case para revocar refresh tokens."""
from datetime import datetime, timezone

from app.v1.auth.domain.entities import RefreshToken


class RevokeRefreshToken:
    """Use Case para revocar un refresh token.

    Invalida un refresh token configurando su expiración al momento actual.
    """

    def execute(self, refresh_token: RefreshToken) -> RefreshToken:
        """Revoca un refresh token haciéndolo expirar inmediatamente.

        Args:
            refresh_token: RefreshToken a revocar

        Returns:
            RefreshToken modificado con expires_at = ahora
        """
        # Fijar la expiración al momento actual para invalidar el token
        refresh_token.expires_at = datetime.now(timezone.utc)

        return refresh_token
