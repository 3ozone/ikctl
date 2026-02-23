"""
Infrastructure Layer Exceptions.

Excepciones específicas de la capa de infraestructura (persistencia, adaptadores externos).
"""


class InfrastructureException(Exception):
    """Base para excepciones de infraestructura."""


class DatabaseConnectionError(InfrastructureException):
    """Error de conexión a la base de datos."""


class DatabaseQueryError(InfrastructureException):
    """Error al ejecutar una consulta en la base de datos."""


class EmailServiceError(InfrastructureException):
    """Error al enviar email a través del servicio externo."""


class SSHConnectionError(InfrastructureException):
    """Error de conexión SSH."""


class JWTProviderError(InfrastructureException):
    """Error al generar o validar JWT tokens."""


class TOTPProviderError(InfrastructureException):
    """Error al generar o validar códigos TOTP."""


class GitHubOAuthError(InfrastructureException):
    """Error en integración OAuth con GitHub."""


class CacheServiceError(InfrastructureException):
    """Error al interactuar con Valkey/cache."""
