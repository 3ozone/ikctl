"""
Application Layer Exceptions — módulo servers.

Excepciones de orquestación de casos de uso. Representan errores de negocio
detectados durante la ejecución de comandos/queries, no errores de dominio ni
de infraestructura.
"""


class UseCaseException(Exception):
    """Base para excepciones de casos de uso del módulo servers."""


class UnauthorizedOperationError(UseCaseException):
    """Operación no autorizada: el usuario no tiene el rol requerido (RNF-16)."""


class DuplicateLocalServerError(UseCaseException):
    """Ya existe un servidor local para este usuario (RN-07)."""


class ServerInUseError(UseCaseException):
    """No se puede eliminar el servidor porque tiene operaciones activas (RN-08)."""


class GroupInUseError(UseCaseException):
    """No se puede eliminar el grupo porque tiene pipelines activos (RN-19)."""


class LocalServerNotAllowedInGroupError(UseCaseException):
    """No se puede añadir un servidor local a un grupo (RNF-16)."""
