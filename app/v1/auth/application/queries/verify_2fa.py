"""Use Case: Verificar código de autenticación de dos factores (2FA)."""

from app.v1.auth.application.interfaces.user_repository import UserRepository
from app.v1.auth.application.interfaces.totp_provider import TOTPProvider
from app.v1.auth.application.exceptions import (
    ResourceNotFoundError,
    UnauthorizedOperationError
)


class Verify2FA:
    """Use Case para verificar un código TOTP de 6 dígitos.

    Valida que el usuario existe, tiene 2FA habilitado y el código es correcto.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        totp_provider: TOTPProvider
    ) -> None:
        """Constructor del use case.

        Args:
            user_repository: Repositorio para gestionar usuarios.
            totp_provider: Proveedor para operaciones TOTP.
        """
        self.user_repository = user_repository
        self.totp_provider = totp_provider

    async def execute(self, user_id: str, code: str) -> bool:
        """Verifica un código 2FA de 6 dígitos.

        Args:
            user_id: ID del usuario.
            code: Código TOTP de 6 dígitos.

        Returns:
            True si el código es válido, False si no.

        Raises:
            ResourceNotFoundError: Si el usuario no existe.
            UnauthorizedOperationError: Si 2FA no está habilitado.
        """
        # Buscar usuario
        user = await self.user_repository.find_by_id(user_id)
        if user is None:
            raise ResourceNotFoundError(
                f"Usuario con ID {user_id} no encontrado"
            )

        # Verificar que 2FA está habilitado
        if not user.is_2fa_enabled:
            raise UnauthorizedOperationError(
                "2FA no está habilitado para este usuario"
            )

        # Verificar que el usuario tiene un secret TOTP configurado
        if user.totp_secret is None:
            raise UnauthorizedOperationError(
                "Usuario no tiene un secret TOTP configurado"
            )

        # Verificar código TOTP
        is_valid = self.totp_provider.verify_code(
            secret=user.totp_secret,
            code=code
        )

        return is_valid
