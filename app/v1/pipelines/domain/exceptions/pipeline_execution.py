"""Excepciones de dominio para la entity PipelineExecution."""
from app.v1.shared.domain.exceptions import DomainException


class PipelineExecutionNotFoundError(DomainException):
    """La ejecución de pipeline no existe o no pertenece al usuario."""