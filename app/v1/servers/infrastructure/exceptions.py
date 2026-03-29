"""Infrastructure Layer Exceptions para el módulo servers."""
from app.v1.shared.infrastructure.exceptions import (
    DatabaseError,
    InfrastructureException,
)


class DatabaseConnectionError(DatabaseError):
    """Error de conexión a la base de datos."""


class DatabaseQueryError(DatabaseError):
    """Error al ejecutar una consulta en la base de datos."""


class SSHConnectionError(InfrastructureException):
    """Error de conexión SSH al servidor remoto."""


class EncryptionError(InfrastructureException):
    """Error al cifrar o descifrar datos sensibles."""
