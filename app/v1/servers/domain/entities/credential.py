"""Entity Credential."""
from dataclasses import dataclass
from datetime import datetime

from app.v1.servers.domain.value_objects.credential_type import CredentialType
from app.v1.servers.domain.exceptions.credential import InvalidCredentialConfigurationError


@dataclass
class Credential:
    """Entity Credential que representa una credencial de acceso reutilizable.

    Una credencial es independiente y puede ser referenciada por múltiples
    servidores o kits. La validación de campos requeridos según el tipo
    se realiza en __post_init__ (RN-18).
    """

    id: str
    user_id: str
    name: str
    type: CredentialType
    username: str | None
    password: str | None
    private_key: str | None
    created_at: datetime
    updated_at: datetime

    def validate(self) -> None:
        """Valida la configuración de la credencial según su tipo (RN-18).

        Llamar explícitamente al crear una credencial nueva (use case de creación).
        No se llama al reconstruir desde persistencia para evitar fallos en datos
        existentes que aún no tengan todos los campos opcionales.

        Raises:
            InvalidCredentialConfigurationError: Si los campos requeridos
                para el tipo de credencial no están presentes.
        """
        credential_type = self.type.value

        if credential_type == "ssh":
            if not self.username:
                raise InvalidCredentialConfigurationError()
            if not self.password and not self.private_key:
                raise InvalidCredentialConfigurationError()

        elif credential_type == "git_https":
            if not self.username or not self.password:
                raise InvalidCredentialConfigurationError()

        elif credential_type == "git_ssh":
            if not self.private_key:
                raise InvalidCredentialConfigurationError()

    def __eq__(self, other: object) -> bool:
        """Igualdad por identidad: dos Credential son iguales si tienen el mismo id."""
        return isinstance(other, Credential) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    # --- Comandos ---

    def update(
        self,
        name: str,
        username: str | None,
        password: str | None,
        private_key: str | None,
        updated_at: datetime,
    ) -> None:
        """Actualiza los campos mutables de la credencial.

        Args:
            name: Nuevo alias de la credencial.
            username: Nuevo nombre de usuario.
            password: Nueva contraseña o PAT.
            private_key: Nueva clave privada SSH.
            updated_at: Timestamp de la actualización.
        """
        self.name = name
        self.username = username
        self.password = password
        self.private_key = private_key
        self.updated_at = updated_at
