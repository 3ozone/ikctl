"""Excepciones de la capa de aplicación del módulo operations."""


class UseCaseException(Exception):
    """Base para todas las excepciones de use cases del módulo operations."""


class OperationNotRetriableError(UseCaseException):
    """La operación no puede reintentarse (no está en estado failed/cancelled_unsafe)."""


class OperationNotRestorableError(UseCaseException):
    """La operación no puede restaurarse (sin backup_files, sin .bak.ikctl o estado incorrecto)."""


class ServerNotActiveError(UseCaseException):
    """El servidor está inactivo y no se puede lanzar una operación sobre él."""


class KitNotUsableError(UseCaseException):
    """El kit no está sincronizado o ha sido eliminado."""


class GroupNotFoundError(UseCaseException):
    """El grupo no existe o no pertenece al usuario."""
