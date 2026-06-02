"""Excepción de dominio para el Value Object PipelineTarget."""
from app.v1.shared.domain.exceptions import DomainException


class InvalidPipelineTargetError(DomainException):
    """El valor de server_id no es válido para un PipelineTarget."""