"""Excepciones de dominio para Credential."""
from app.v1.shared.domain.exceptions import DomainException


class InvalidCredentialTypeError(DomainException):
    """Tipo de credencial inválido. Solo se permiten: ssh, git_https, git_ssh."""


class CredentialNotFoundError(DomainException):
    """Credencial no encontrada."""


class InvalidCredentialConfigurationError(DomainException):
    """Configuración de credencial inválida según su tipo (RN-18).

    - ssh: requiere username y al menos password o private_key.
    - git_https: requiere username y password (PAT).
    - git_ssh: requiere private_key.
    """


class CredentialInUseError(DomainException):
    """No se puede eliminar la credencial porque está siendo usada por uno o más servidores (RN-06)."""
