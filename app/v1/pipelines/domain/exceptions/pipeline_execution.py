"""Excepciones de dominio para la entity PipelineExecution."""
from app.v1.shared.domain.exceptions import DomainException


class PipelineExecutionNotFoundError(DomainException):
    """La ejecución de pipeline no existe o no pertenece al usuario."""


class PipelineExecutionNotCancellableError(DomainException):
    """La ejecución de pipeline no puede cancelarse en su estado actual."""