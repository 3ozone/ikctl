"""
Interface para el servicio de envío de emails.

Define el contrato que será implementado en infrastructure/adapters/.
"""
from abc import ABC, abstractmethod


class EmailService(ABC):
    """Contrato para operaciones de envío de emails."""

    @abstractmethod
    async def send_verification_email(self, to_email: str, token: str, user_name: str) -> None:
        """
        Envía email de verificación tras registro.

        Args:
            to_email: Email destino
            token: Token de verificación (para construir link)
            user_name: Nombre del usuario (personalización)

        Raises:
            EmailServiceError: Error al enviar email
        """

    @abstractmethod
    async def send_password_reset_email(self, to_email: str, token: str, user_name: str) -> None:
        """
        Envía email con link para resetear contraseña.

        Args:
            to_email: Email destino
            token: Token de reset (para construir link)
            user_name: Nombre del usuario (personalización)

        Raises:
            EmailServiceError: Error al enviar email
        """

    @abstractmethod
    async def send_password_changed_notification(self, to_email: str, user_name: str) -> None:
        """
        Envía notificación de cambio de contraseña exitoso.

        Args:
            to_email: Email destino
            user_name: Nombre del usuario

        Raises:
            EmailServiceError: Error al enviar email
        """

    @abstractmethod
    async def send_2fa_enabled_notification(self, to_email: str, user_name: str) -> None:
        """
        Envía notificación de activación de 2FA.

        Args:
            to_email: Email destino
            user_name: Nombre del usuario

        Raises:
            EmailServiceError: Error al enviar email
        """
