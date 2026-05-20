"""Excepciones de dominio para Repository."""
from app.v1.shared.domain.exceptions import DomainException


class InvalidSyncStatusError(DomainException):
    """Estado de sincronización inválido. Solo se permiten: never_synced, synced, sync_error."""


class RepositoryNotFoundError(DomainException):
    """Repositorio no encontrado o no pertenece al usuario."""
