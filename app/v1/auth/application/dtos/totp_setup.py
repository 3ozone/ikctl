"""
DTO para configuración de TOTP (2FA).

Usado por Enable2FA use case.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TOTPSetup:
    """Datos necesarios para configurar 2FA en app autenticadora."""

    secret: str
    qr_code_uri: str
    provisioning_uri: str
    backup_codes: list[str]
