"""Excepciones base del dominio - Shared Layer.

Estas excepciones base deben ser heredadas por excepciones específicas
de cada módulo (auth, servers, operations, users).

Según ADR-006, usamos excepciones tradicionales de Python (no Result/Either).
"""


class DomainException(Exception):
    """
    Excepción base para errores de dominio.

    Los errores de dominio representan violaciones de reglas de negocio
    o invariantes del modelo. Ejemplos:
    - Email con formato inválido
    - Password que no cumple requisitos de complejidad
    - Usuario que ya existe
    - Entidad en estado inválido

    Los módulos deben heredar de esta clase para sus excepciones específicas:
    - auth.domain.exceptions.InvalidEmailError(DomainException)
    - servers.domain.exceptions.InvalidServerConfigError(DomainException)
    - operations.domain.exceptions.InvalidOperationStateError(DomainException)
    """


class ValidationError(DomainException):
    """Error de validación de datos de entrada."""


class EntityNotFoundError(DomainException):
    """Error cuando una entidad no existe en el sistema."""


class EntityAlreadyExistsError(DomainException):
    """Error cuando se intenta crear una entidad que ya existe."""


class InvalidStateError(DomainException):
    """Error cuando una entidad está en un estado inválido para la operación."""


class BusinessRuleViolationError(DomainException):
    """Error cuando se viola una regla de negocio."""
