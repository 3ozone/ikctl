"""EmailService - Implementación de IEmailService usando aiosmtplib."""
from email.mime.text import MIMEText

import aiosmtplib

from app.v1.auth.application.interfaces.email_service import IEmailService
from app.v1.auth.infrastructure.exceptions import EmailServiceError


class EmailService(IEmailService):
    """Implementación de IEmailService usando aiosmtplib."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        from_name: str,
        base_url: str
    ):
        """Inicializa el servicio de email.

        Args:
            smtp_host: Host del servidor SMTP
            smtp_port: Puerto SMTP (587 para TLS, 465 para SSL)
            smtp_user: Usuario SMTP
            smtp_password: Contraseña SMTP
            from_email: Email remitente
            from_name: Nombre del remitente
            base_url: URL base de la aplicación (para construir links)
        """
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._from_email = from_email
        self._from_name = from_name
        self._base_url = base_url

    async def send_verification_email(
        self,
        to_email: str,
        token: str,
        user_name: str
    ) -> None:
        """Envía email de verificación tras registro.

        Args:
            to_email: Email destino
            token: Token de verificación
            user_name: Nombre del usuario

        Raises:
            EmailServiceError: Error al enviar email
        """
        try:
            verification_link = f"{self._base_url}/verify-email?token={token}"

            subject = "Verifica tu cuenta en ikctl"
            html_body = f"""
            <html>
                <body>
                    <h2>¡Hola {user_name}!</h2>
                    <p>Gracias por registrarte en ikctl.</p>
                    <p>Por favor, verifica tu cuenta haciendo clic en el siguiente enlace:</p>
                    <p><a href="{verification_link}">Verificar mi cuenta</a></p>
                    <p>Si no creaste esta cuenta, puedes ignorar este email.</p>
                    <p>El enlace expira en 24 horas.</p>
                    <br>
                    <p>Saludos,<br>El equipo de ikctl</p>
                </body>
            </html>
            """

            await self._send_email(to_email, subject, html_body)

        except Exception as e:
            raise EmailServiceError(
                f"Error enviando email de verificación: {str(e)}"
            ) from e

    async def send_password_reset_email(
        self,
        to_email: str,
        token: str,
        user_name: str
    ) -> None:
        """Envía email con link para resetear contraseña.

        Args:
            to_email: Email destino
            token: Token de reset
            user_name: Nombre del usuario

        Raises:
            EmailServiceError: Error al enviar email
        """
        try:
            reset_link = f"{self._base_url}/reset-password?token={token}"

            subject = "Restablece tu contraseña en ikctl"
            html_body = f"""
            <html>
                <body>
                    <h2>¡Hola {user_name}!</h2>
                    <p>Recibimos una solicitud para restablecer tu contraseña.</p>
                    <p>Haz clic en el siguiente enlace para crear una nueva contraseña:</p>
                    <p><a href="{reset_link}">Restablecer mi contraseña</a></p>
                    <p>Si no solicitaste este cambio, puedes ignorar este email.</p>
                    <p>El enlace expira en 1 hora.</p>
                    <br>
                    <p>Saludos,<br>El equipo de ikctl</p>
                </body>
            </html>
            """

            await self._send_email(to_email, subject, html_body)

        except Exception as e:
            raise EmailServiceError(
                f"Error enviando email de reset: {str(e)}"
            ) from e

    async def send_password_changed_notification(
        self,
        to_email: str,
        user_name: str
    ) -> None:
        """Envía notificación de cambio de contraseña exitoso.

        Args:
            to_email: Email destino
            user_name: Nombre del usuario

        Raises:
            EmailServiceError: Error al enviar email
        """
        try:
            subject = "Tu contraseña ha sido cambiada"
            html_body = f"""
            <html>
                <body>
                    <h2>¡Hola {user_name}!</h2>
                    <p>Te confirmamos que tu contraseña ha sido cambiada exitosamente.</p>
                    <p>Si no realizaste este cambio, contacta con soporte inmediatamente.</p>
                    <br>
                    <p>Saludos,<br>El equipo de ikctl</p>
                </body>
            </html>
            """

            await self._send_email(to_email, subject, html_body)

        except Exception as e:
            raise EmailServiceError(
                f"Error enviando notificación de cambio de contraseña: {str(e)}"
            ) from e

    async def send_2fa_enabled_notification(
        self,
        to_email: str,
        user_name: str
    ) -> None:
        """Envía notificación de activación de 2FA.

        Args:
            to_email: Email destino
            user_name: Nombre del usuario

        Raises:
            EmailServiceError: Error al enviar email
        """
        try:
            subject = "Autenticación de dos factores activada"
            html_body = f"""
            <html>
                <body>
                    <h2>¡Hola {user_name}!</h2>
                    <p>La autenticación de dos factores (2FA) ha sido activada en tu cuenta.</p>
                    <p>Ahora tu cuenta está más segura.</p>
                    <p>Si no fuiste tú quien activó 2FA, contacta con soporte inmediatamente.</p>
                    <br>
                    <p>Saludos,<br>El equipo de ikctl</p>
                </body>
            </html>
            """

            await self._send_email(to_email, subject, html_body)

        except Exception as e:
            raise EmailServiceError(
                f"Error enviando notificación de 2FA: {str(e)}"
            ) from e

    async def _send_email(self, to_email: str, subject: str, html_body: str) -> None:
        """Método privado para enviar email via SMTP.

        Args:
            to_email: Email destino
            subject: Asunto del email
            html_body: Cuerpo HTML del email

        Raises:
            Exception: Error SMTP o de conexión
        """
        # Crear mensaje HTML directamente
        message = MIMEText(html_body, "html")
        message["From"] = f"{self._from_name} <{self._from_email}>"
        message["To"] = to_email
        message["Subject"] = subject

        # Enviar email
        async with aiosmtplib.SMTP(
            hostname=self._smtp_host,
            port=self._smtp_port,
            use_tls=True
        ) as smtp:
            await smtp.login(self._smtp_user, self._smtp_password)
            await smtp.send_message(message)
