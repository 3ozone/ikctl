"""Excepciones de dominio para Group."""
from app.v1.shared.domain.exceptions import DomainException


class GroupNotFoundError(DomainException):
    """Grupo no encontrado."""
