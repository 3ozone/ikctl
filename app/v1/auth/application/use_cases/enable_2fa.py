"""Use Case: Habilitar autenticación de dos factores (2FA)."""
from datetime import datetime, timezone

from app.v1.auth.application.interfaces.user_repository import UserRepository
from app.v1.auth.application.interfaces.totp_provider import TOTPProvider
from app.v1.auth.application.exceptions import ResourceNotFoundError


class Enable2FA:
    """Use Case para habilitar 2FA en una cuenta de usuario.

    Genera un secret TOTP y un QR code para escanear con apps 2FA.
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

    async def execute(self, user_id: str) -> dict[str, str]:
        """Habilita 2FA para un usuario.

        Args:
            user_id: ID del usuario.

        Returns:
            Dict con 'secret' (base32) y 'qr_code' (data URI).

        Raises:
            ResourceNotFoundError: Si el usuario no existe.
        """
        # Buscar usuario
        user = await self.user_repository.find_by_id(user_id)
        if user is None:
            raise ResourceNotFoundError(
                f"Usuario con ID {user_id} no encontrado"
            )

        # Generar secret TOTP
        secret = self.totp_provider.generate_secret()

        # Generar QR code
        qr_code = self.totp_provider.generate_qr_code(
            secret=secret,
            user_email=user.email.value,
            issuer="ikctl"
        )

        # Actualizar usuario con 2FA habilitado
        user.totp_secret = secret
        user.is_2fa_enabled = True
        user.updated_at = datetime.now(timezone.utc)

        # Persistir cambios
        await self.user_repository.update(user)

        # Retornar datos para configurar app 2FA
        return {
            "secret": secret,
            "qr_code": qr_code
        }
