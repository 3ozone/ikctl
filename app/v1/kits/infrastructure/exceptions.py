"""Infrastructure Layer Exceptions para el módulo kits."""
from app.v1.shared.infrastructure.exceptions import (
    DatabaseError,
    InfrastructureException,
)


class DatabaseConnectionError(DatabaseError):
    """Error de conexión a la base de datos."""


class DatabaseQueryError(DatabaseError):
    """Error al ejecutar una consulta en la base de datos."""


class GitClientError(InfrastructureException):
    """Error al interactuar con un repositorio Git remoto."""
