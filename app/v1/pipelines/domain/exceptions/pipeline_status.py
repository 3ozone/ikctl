"""Excepción de dominio para el Value Object PipelineStatus."""
from app.v1.shared.domain.exceptions import DomainException


class InvalidPipelineStatusError(DomainException):
    """El valor de estado de pipeline no es válido."""