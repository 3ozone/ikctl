"""
Infrastructure Layer Exceptions.

Excepciones específicas de la capa de infraestructura (persistencia, adaptadores externos).
"""

from app.v1.shared.infrastructure.exceptions import (
    InfrastructureException,
    DatabaseError,
    ExternalServiceError,
    CacheError,
)


class DatabaseConnectionError(DatabaseError):
    """Error de conexión a la base de datos."""


class DatabaseQueryError(DatabaseError):
    """Error al ejecutar una consulta en la base de datos."""


class EmailServiceError(ExternalServiceError):
    """Error al enviar email a través del servicio externo."""


class SSHConnectionError(InfrastructureException):
    """Error de conexión SSH."""


class JWTProviderError(InfrastructureException):
    """Error al generar o validar JWT tokens."""


class TOTPProviderError(InfrastructureException):
    """Error al generar o validar códigos TOTP."""


class GitHubOAuthError(ExternalServiceError):
    """Error en integración OAuth con GitHub."""


class CacheServiceError(CacheError):
    """Error al interactuar con Valkey/cache."""
