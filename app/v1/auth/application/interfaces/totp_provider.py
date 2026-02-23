"""
Interface para el proveedor de TOTP (Time-based One-Time Password).

Define el contrato que será implementado en infrastructure/adapters/.
"""
from abc import ABC, abstractmethod


class ITOTPProvider(ABC):
    """Contrato para operaciones de 2FA con TOTP."""

    @abstractmethod
    def generate_secret(self) -> str:
        """
        Genera un secret aleatorio para TOTP.

        Returns:
            Secret base32 (compatible con Google Authenticator, Authy)

        Raises:
            InfrastructureException: Error al generar secret
        """

    @abstractmethod
    def generate_qr_code(self, secret: str, user_email: str, issuer: str = "ikctl") -> str:
        """
        Genera un QR code en formato data URI para escanear con app 2FA.

        Args:
            secret: Secret TOTP base32
            user_email: Email del usuario (identificación en app)
            issuer: Nombre del emisor (aparece en app)

        Returns:
            Data URI del QR code (data:image/png;base64,...)

        Raises:
            InfrastructureException: Error al generar QR
        """

    @abstractmethod
    def verify_code(self, secret: str, code: str) -> bool:
        """
        Verifica un código TOTP de 6 dígitos.

        Args:
            secret: Secret TOTP base32
            code: Código de 6 dígitos del usuario

        Returns:
            True si código válido, False si no

        Raises:
            InfrastructureException: Error al verificar
        """

    @abstractmethod
    def get_provisioning_uri(self, secret: str, user_email: str, issuer: str = "ikctl") -> str:
        """
        Genera URI de provisionamiento para configuración manual.

        Args:
            secret: Secret TOTP base32
            user_email: Email del usuario
            issuer: Nombre del emisor

        Returns:
            URI en formato otpauth://totp/...

        Raises:
            InfrastructureException: Error al generar URI
        """
