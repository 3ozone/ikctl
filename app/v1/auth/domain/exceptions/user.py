"""Excepciones de dominio para User."""
from app.v1.shared.domain.exceptions import (
    DomainException,
    EntityNotFoundError,
    EntityAlreadyExistsError,
)


class InvalidUserError(DomainException):
    """Error cuando los datos del usuario son inválidos."""


class UserNotFoundError(EntityNotFoundError):
    """Error cuando el usuario no existe."""


class UserAlreadyExistsError(EntityAlreadyExistsError):
    """Error cuando se intenta crear un usuario que ya existe."""
