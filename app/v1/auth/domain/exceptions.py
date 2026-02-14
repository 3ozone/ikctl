"""Excepciones del dominio de autenticación."""


class DomainException(Exception):
    """Excepción base del dominio."""


class InvalidEmailError(DomainException):
    """Error cuando el formato de email es inválido."""


class InvalidPasswordError(DomainException):
    """Error cuando el password no cumple requisitos de complejidad."""


class InvalidUserError(DomainException):
    """Error cuando los datos del usuario son inválidos."""


class UserNotFoundError(DomainException):
    """Error cuando el usuario no existe."""


class UserAlreadyExistsError(DomainException):
    """Error cuando se intenta crear un usuario que ya existe."""


class InvalidJWTTokenError(DomainException):
    """Error cuando el JWT Token es inválido."""


class InvalidRefreshTokenError(DomainException):
    """Error cuando el RefreshToken es inválido."""


class InvalidVerificationTokenError(DomainException):
    """Error cuando el VerificationToken es inválido."""
