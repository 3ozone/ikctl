"""
Application Layer Exceptions.

Excepciones específicas de la capa de aplicación (casos de uso).
"""


class UseCaseException(Exception):
    """Base para excepciones de casos de uso."""


class UnauthorizedOperationError(UseCaseException):
    """Operación no autorizada por permisos o estado del usuario."""


class EmailAlreadyExistsError(UseCaseException):
    """Email ya está registrado en el sistema."""


class TokenExpiredError(UseCaseException):
    """Token ha expirado."""


class InvalidTokenError(UseCaseException):
    """Token es inválido o ha sido revocado."""


class UserBlockedError(UseCaseException):
    """Usuario bloqueado temporalmente por intentos fallidos."""


class SessionLimitExceededError(UseCaseException):
    """Usuario ha excedido el límite de sesiones simultáneas."""


class TwoFactorRequiredError(UseCaseException):
    """Se requiere verificación 2FA para completar la operación."""


class ResourceNotFoundError(UseCaseException):
    """Recurso solicitado no existe."""
