"""Excepciones de dominio para la entity Operation."""
from app.v1.shared.domain.exceptions import DomainException


class OperationNotFoundError(DomainException):
    """La operación no existe o no pertenece al usuario."""


class InvalidOperationTransitionError(DomainException):
    """La transición de estado solicitada no es válida para el estado actual."""


class InvalidOperationStatusError(DomainException):
    """El valor de estado de operación no es válido."""
