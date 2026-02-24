"""Excepciones base de infraestructura - Shared Layer.

Estas excepciones base deben ser heredadas por excepciones específicas
de cada módulo (auth, servers, operations, users).

Según ADR-006, las excepciones de infraestructura se wrappean y propagan
hacia capas superiores sin mezclar con lógica de negocio.
"""


class InfrastructureException(Exception):
    """
    Excepción base para errores de infraestructura.

    Los errores de infraestructura representan fallos técnicos externos:
    - Errores de base de datos (conexión, queries, constraints)
    - Errores de servicios externos (SMTP, APIs HTTP, SSH)
    - Errores de cache (Valkey/Redis)
    - Errores de event bus (publicación, consumo)

    Los módulos deben heredar de esta clase para sus excepciones específicas:
    - auth.infrastructure.exceptions.DatabaseConnectionError(InfrastructureException)
    - servers.infrastructure.exceptions.SSHConnectionError(InfrastructureException)
    - operations.infrastructure.exceptions.KubernetesAPIError(InfrastructureException)
    """


class DatabaseError(InfrastructureException):
    """Error de base de datos."""


class DatabaseConnectionError(DatabaseError):
    """Error al conectar con la base de datos."""


class DatabaseQueryError(DatabaseError):
    """Error al ejecutar query en la base de datos."""


class ExternalServiceError(InfrastructureException):
    """Error en servicio externo."""


class HTTPClientError(ExternalServiceError):
    """Error en cliente HTTP (timeout, connection, etc)."""


class CacheError(InfrastructureException):
    """Error en cache (Valkey/Redis)."""


class MessageBusError(InfrastructureException):
    """Error en message bus / event bus."""


class ConfigurationError(InfrastructureException):
    """Error de configuración del sistema."""
