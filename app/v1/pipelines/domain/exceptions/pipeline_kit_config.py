"""Excepción de dominio para el Value Object PipelineKitConfig."""
from app.v1.shared.domain.exceptions import DomainException


class InvalidPipelineKitConfigError(DomainException):
    """El valor de kit_id o debug_level no es válido para un PipelineKitConfig."""