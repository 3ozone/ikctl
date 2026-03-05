"""Logger estructurado centralizado — structlog con JSON output y context injection.

Uso:
    from app.v1.shared.infrastructure.logger import get_logger

    logger = get_logger(__name__)
    logger.info("user_registered", user_id="abc", email="user@example.com")

Desacoplamiento:
    Los use cases NO importan este módulo. El logging ocurre exclusivamente en:
    - Middleware FastAPI (request/response + correlation_id)
    - InMemoryEventBus (eventos publicados/consumidos)
    - Adaptadores/repositories (operaciones externas)
    - Exception handlers (errores con contexto)
"""
import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO", json_output: bool = True) -> None:
    """Configura structlog con JSON output y procesadores estándar.

    Args:
        log_level: Nivel de log ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
        json_output: Si True, emite JSON. Si False, emite texto legible (desarrollo).
    """
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Devuelve un logger estructurado vinculado al nombre del módulo.

    Args:
        name: Normalmente __name__ del módulo que llama.

    Returns:
        Logger structlog listo para usar.
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: object) -> None:
    """Añade contexto global al logger para el request actual (correlation_id, user_id, etc.).

    Debe llamarse al inicio de cada request (en middleware).
    Se limpia automáticamente al finalizar el request con clear_context().

    Args:
        **kwargs: Pares clave-valor a añadir al contexto (ej: request_id="abc", user_id="123").
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Limpia el contexto del logger al finalizar el request."""
    structlog.contextvars.clear_contextvars()
