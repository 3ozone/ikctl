"""Infrastructure Layer Exceptions para el módulo operations."""
from app.v1.shared.infrastructure.exceptions import (
    DatabaseError,
    InfrastructureException,
)


class DatabaseConnectionError(DatabaseError):
    """Error de conexión a la base de datos."""


class DatabaseQueryError(DatabaseError):
    """Error al ejecutar una consulta en la base de datos."""


class EncryptionError(InfrastructureException):
    """Error al cifrar o descifrar datos sensibles."""


class SSHConnectionError(InfrastructureException):
    """Error al establecer o mantener una conexión SSH."""


class SSHCommandError(InfrastructureException):
    """Error al ejecutar un comando remoto vía SSH."""
