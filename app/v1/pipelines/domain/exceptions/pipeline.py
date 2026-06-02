"""Excepciones de dominio para la entity Pipeline."""
from app.v1.shared.domain.exceptions import DomainException


class PipelineNotFoundError(DomainException):
    """El pipeline no existe o no pertenece al usuario."""