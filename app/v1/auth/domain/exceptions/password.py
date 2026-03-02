"""Excepción de dominio para Password."""
from app.v1.shared.domain.exceptions import DomainException


class InvalidPasswordError(DomainException):
    """Error cuando el password no cumple requisitos de complejidad."""
