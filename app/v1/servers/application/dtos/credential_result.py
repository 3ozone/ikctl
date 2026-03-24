"""
DTO para resultado de operaciones sobre credenciales.

Nunca expone password ni private_key — solo metadatos seguros.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CredentialResult:
    """Resultado de crear o actualizar una credencial.

    No incluye password ni private_key por seguridad.
    """

    credential_id: str
    user_id: str
    name: str
    credential_type: str
    username: str | None
    created_at: datetime
    updated_at: datetime
