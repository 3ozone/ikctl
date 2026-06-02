"""Excepciones de infraestructura del módulo pipelines."""


class InfrastructureException(Exception):
    """Base para excepciones de infraestructura del módulo pipelines."""


class DatabaseQueryError(InfrastructureException):
    """Error al ejecutar una consulta o persistencia en base de datos."""
