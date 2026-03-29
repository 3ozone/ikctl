"""
DTO para resultado de operaciones sobre servidores.

No expone datos sensibles de credenciales — solo credential_id como referencia.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ServerResult:
    """Resultado de crear o actualizar un servidor.

    Devuelve solo metadatos seguros. No incluye datos de la credencial asociada.
    """

    server_id: str
    user_id: str
    name: str
    server_type: str
    status: str
    host: str | None
    port: int | None
    credential_id: str | None
    description: str | None
    os_id: str | None
    os_version: str | None
    os_name: str | None
    created_at: datetime
    updated_at: datetime
