"""Entity Server."""
from dataclasses import dataclass
from datetime import datetime

from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.exceptions.server import InvalidServerConfigurationError


@dataclass
class Server:
    """Entity Server que representa un servidor gestionado por el sistema.

    Puede ser de tipo remote (acceso SSH) o local (ejecución directa).
    La validación de configuración según el tipo se realiza en __post_init__.
    """

    id: str
    user_id: str
    name: str
    type: ServerType
    status: ServerStatus
    host: str | None
    port: int | None
    credential_id: str | None
    description: str | None
    os_id: str | None
    os_version: str | None
    os_name: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """Valida la configuración del servidor según su tipo.

        Raises:
            InvalidServerConfigurationError: Si los campos no son coherentes
                con el tipo de servidor (remote/local).
        """
        if self.type.value == "remote":
            if not self.host:
                raise InvalidServerConfigurationError()
            if not self.credential_id:
                raise InvalidServerConfigurationError()

        elif self.type.value == "local":
            if self.host:
                raise InvalidServerConfigurationError()
            if self.credential_id:
                raise InvalidServerConfigurationError()

    def __eq__(self, other: object) -> bool:
        """Igualdad por identidad: dos Server son iguales si tienen el mismo id."""
        return isinstance(other, Server) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    # --- Comandos ---

    def activate(self) -> None:
        """Activa el servidor cambiando su estado a active."""
        self.status = ServerStatus("active")

    def deactivate(self) -> None:
        """Desactiva el servidor cambiando su estado a inactive."""
        self.status = ServerStatus("inactive")

    def update_os_info(self, os_id: str, os_version: str, os_name: str) -> None:
        """Actualiza la información del sistema operativo detectado.

        Args:
            os_id: Identificador del SO (ej: ubuntu, debian).
            os_version: Versión del SO (ej: 22.04).
            os_name: Nombre completo del SO (ej: Ubuntu 22.04 LTS).
        """
        self.os_id = os_id
        self.os_version = os_version
        self.os_name = os_name

    # --- Queries ---

    def is_active(self) -> bool:
        """Devuelve True si el servidor está activo."""
        return self.status.value == "active"

    def is_local(self) -> bool:
        """Devuelve True si el servidor es de tipo local."""
        return self.type.value == "local"

    def is_remote(self) -> bool:
        """Devuelve True si el servidor es de tipo remote."""
        return self.type.value == "remote"
