"""Entity Group."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Group:
    """Entity Group que representa un grupo de servidores.

    Un grupo es un conjunto de servidores que puede usarse como target
    en pipelines, ejecutando el pipeline en todos los servidores del grupo.
    """

    id: str
    user_id: str
    name: str
    description: str | None
    server_ids: list[str]
    created_at: datetime
    updated_at: datetime

    def __eq__(self, other: object) -> bool:
        """Igualdad por identidad: dos Group son iguales si tienen el mismo id."""
        return isinstance(other, Group) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    # --- Comandos ---

    def add_server(self, server_id: str) -> None:
        """Añade un servidor al grupo.

        Args:
            server_id: Identificador del servidor a añadir.
        """
        self.server_ids.append(server_id)

    def remove_server(self, server_id: str) -> None:
        """Elimina un servidor del grupo.

        Args:
            server_id: Identificador del servidor a eliminar.
        """
        self.server_ids.remove(server_id)

    def update(
        self,
        name: str,
        description: str | None,
        server_ids: list[str],
        updated_at: datetime,
    ) -> None:
        """Actualiza los campos mutables del grupo.

        Args:
            name: Nuevo nombre del grupo.
            description: Nueva descripción del grupo.
            server_ids: Nueva lista de identificadores de servidores.
            updated_at: Timestamp de la actualización.
        """
        self.name = name
        self.description = description
        self.server_ids = server_ids
        self.updated_at = updated_at
