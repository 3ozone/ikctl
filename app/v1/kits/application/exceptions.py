"""
Application Layer Exceptions — módulo kits.

Excepciones de orquestación de casos de uso. Representan errores de negocio
detectados durante la ejecución de comandos/queries, no errores de dominio ni
de infraestructura.
"""


class UseCaseException(Exception):
    """Base para excepciones de casos de uso del módulo kits."""


class RepositoryNotFoundError(UseCaseException):
    """El repositorio no existe o no pertenece al usuario (RN-01)."""


class KitNotFoundError(UseCaseException):
    """El kit no existe o no pertenece al usuario (RN-01)."""


class KitNotSyncedError(UseCaseException):
    """El kit no está sincronizado y no puede usarse en operaciones."""


class KitNotUsableError(UseCaseException):
    """El kit no es usable: está eliminado o en error de sync."""


class InvalidGitCredentialTypeError(UseCaseException):
    """La credencial proporcionada no es de tipo git_https o git_ssh (RN-23)."""


class ManifestValidationError(UseCaseException):
    """El ikctl.yaml del kit es inválido (RN-21)."""


class RepositoryInUseError(UseCaseException):
    """No se puede eliminar el repositorio porque sus kits tienen referencias activas (RN-30)."""


class MissingRootManifestError(UseCaseException):
    """No se encontró ikctl.yaml en la raíz del repositorio durante el sync."""
