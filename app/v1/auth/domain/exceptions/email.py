"""Excepción de dominio para Email."""
from app.v1.shared.domain.exceptions import DomainException


class InvalidEmailError(DomainException):
    """Error cuando el formato de email es inválido."""
