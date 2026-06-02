"""Excepciones de la capa de aplicación del módulo pipelines."""


class UseCaseException(Exception):
    """Base para todas las excepciones de use cases del módulo pipelines."""


class PipelineInProgressError(UseCaseException):
    """El pipeline tiene ejecuciones activas y no puede modificarse ni eliminarse."""


class LocalServerInPipelineError(UseCaseException):
    """Un servidor local no puede formar parte de un pipeline."""


class PipelineNotLaunchableError(UseCaseException):
    """El pipeline no puede lanzarse (kit no usable u otra condición)."""