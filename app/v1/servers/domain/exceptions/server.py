"""Excepciones de dominio para Server."""
from app.v1.shared.domain.exceptions import DomainException


class InvalidServerTypeError(DomainException):
    """Tipo de servidor inválido. Solo se permiten: remote, local."""


class InvalidServerStatusError(DomainException):
    """Estado de servidor inválido. Solo se permiten: active, inactive."""


class ServerNotFoundError(DomainException):
    """Servidor no encontrado."""


class InvalidServerConfigurationError(DomainException):
    """Configuración de servidor inválida según su tipo.

    - remote: requiere host y credential_id.
    - local: no puede tener host ni credential_id.
    """
