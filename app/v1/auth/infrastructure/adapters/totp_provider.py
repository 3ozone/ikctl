"""PyOTPTOTPProvider - Implementación concreta de TOTPProvider usando pyotp."""
import base64
import io

import pyotp
import qrcode
from qrcode.constants import ERROR_CORRECT_L

from app.v1.auth.application.interfaces.totp_provider import TOTPProvider
from app.v1.auth.infrastructure.exceptions import InfrastructureException


class PyOTPTOTPProvider(TOTPProvider):
    """Implementación de TOTPProvider usando pyotp y qrcode."""

    def generate_secret(self) -> str:
        """Genera un secret aleatorio para TOTP.

        Returns:
            Secret base32 (compatible con Google Authenticator, Authy)

        Raises:
            InfrastructureException: Error al generar secret
        """
        try:
            return pyotp.random_base32()
        except Exception as e:
            raise InfrastructureException(
                f"Error generando secret TOTP: {str(e)}"
            ) from e

    def generate_qr_code(
        self,
        secret: str,
        user_email: str,
        issuer: str = "ikctl"
    ) -> str:
        """Genera un QR code en formato data URI para escanear con app 2FA.

        Args:
            secret: Secret TOTP base32
            user_email: Email del usuario (identificación en app)
            issuer: Nombre del emisor (aparece en app)

        Returns:
            Data URI del QR code (data:image/png;base64,...)

        Raises:
            InfrastructureException: Error al generar QR
        """
        try:
            # Obtener URI de provisionamiento
            uri = self.get_provisioning_uri(secret, user_email, issuer)

            # Generar QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(uri)
            qr.make(fit=True)

            # Convertir a imagen
            img = qr.make_image(fill_color="black", back_color="white")

            # Convertir imagen a data URI base64
            buffer = io.BytesIO()
            img.save(buffer, "PNG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode()

            return f"data:image/png;base64,{img_base64}"

        except Exception as e:
            raise InfrastructureException(
                f"Error generando QR code: {str(e)}"
            ) from e

    def verify_code(self, secret: str, code: str) -> bool:
        """Verifica un código TOTP de 6 dígitos.

        Args:
            secret: Secret TOTP base32
            code: Código de 6 dígitos del usuario

        Returns:
            True si código válido, False si no

        Raises:
            InfrastructureException: Error al verificar
        """
        try:
            # Validar formato del código
            if not code or not isinstance(code, str):
                return False

            # Debe ser exactamente 6 dígitos
            if len(code) != 6 or not code.isdigit():
                return False

            # Verificar con pyotp (valid_window=1 permite 1 ventana antes/después)
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=1)

        except Exception as e:
            raise InfrastructureException(
                f"Error verificando código TOTP: {str(e)}"
            ) from e

    def get_provisioning_uri(
        self,
        secret: str,
        user_email: str,
        issuer: str = "ikctl"
    ) -> str:
        """Genera URI de provisionamiento para configuración manual.

        Args:
            secret: Secret TOTP base32
            user_email: Email del usuario
            issuer: Nombre del emisor

        Returns:
            URI en formato otpauth://totp/...

        Raises:
            InfrastructureException: Error al generar URI
        """
        try:
            totp = pyotp.TOTP(secret)
            return totp.provisioning_uri(
                name=user_email,
                issuer_name=issuer
            )
        except Exception as e:
            raise InfrastructureException(
                f"Error generando provisioning URI: {str(e)}"
            ) from e
