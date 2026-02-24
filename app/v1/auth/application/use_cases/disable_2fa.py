"""Use Case: Deshabilitar autenticación de dos factores (2FA)."""
from datetime import datetime, timezone

from app.v1.auth.application.interfaces.user_repository import UserRepository
from app.v1.auth.application.exceptions import ResourceNotFoundError


class Disable2FA:
    """Use Case para deshabilitar 2FA en una cuenta de usuario.

    Elimina el secret TOTP y marca 2FA como deshabilitado.
    """

    def __init__(self, user_repository: UserRepository) -> None:
        """Constructor del use case.

        Args:
            user_repository: Repositorio para gestionar usuarios.
        """
        self.user_repository = user_repository

    async def execute(self, user_id: str) -> None:
        """Deshabilita 2FA para un usuario.

        Args:
            user_id: ID del usuario.

        Raises:
            ResourceNotFoundError: Si el usuario no existe.
        """
        # Buscar usuario
        user = await self.user_repository.find_by_id(user_id)
        if user is None:
            raise ResourceNotFoundError(
                f"Usuario con ID {user_id} no encontrado"
            )

        # Deshabilitar 2FA
        user.totp_secret = None
        user.is_2fa_enabled = False
        user.updated_at = datetime.now(timezone.utc)

        # Persistir cambios
        await self.user_repository.update(user)
