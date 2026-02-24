"""EventBus InMemory para MVP."""
from abc import ABC, abstractmethod
from typing import Dict, List
import logging

from app.v1.shared.domain.events import DomainEvent

logger = logging.getLogger(__name__)


class EventHandler(ABC):
    """
    Interfaz para handlers de eventos de dominio.

    Los handlers deben ser idempotentes: procesar el mismo evento
    múltiples veces debe producir el mismo resultado (ADR-008).
    """

    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """
        Procesar un evento de dominio.

        Args:
            event: Evento a procesar

        Raises:
            Exception: Los handlers pueden lanzar excepciones que serán loggeadas
                       pero no detendrán otros handlers.
        """


class EventBus:
    """
    Event Bus InMemory para MVP.

    Implementación sincrónica en mismo proceso. Los eventos se publican
    y procesan inmediatamente por todos los handlers suscritos.

    Características:
    - Múltiples handlers por tipo de evento
    - Handlers suscritos múltiples veces solo se llaman una vez
    - Excepciones en handlers no detienen otros handlers
    - Thread-safe para uso en aplicación async

    Migración futura: Esta interface permite cambiar a Valkey Streams
    sin modificar código de negocio (ADR-008 Fase 2).
    """

    def __init__(self) -> None:
        """Inicializar EventBus con diccionario vacío de suscriptores."""
        self._subscribers: Dict[str, List[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Suscribir un handler a un tipo de evento.

        Si el handler ya está suscrito, no se añade duplicado.

        Args:
            event_type: Tipo de evento (ej: "UserRegistered")
            handler: Handler que procesará el evento
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        # Evitar duplicados (test 7)
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Desuscribir un handler de un tipo de evento.

        Si el handler no está suscrito, no hace nada (no lanza error).

        Args:
            event_type: Tipo de evento
            handler: Handler a desuscribir
        """
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event: DomainEvent) -> None:
        """
        Publicar un evento a todos los handlers suscritos.

        Los handlers se ejecutan secuencialmente. Si un handler lanza
        excepción, se loggea pero no detiene otros handlers (ADR-008).

        Args:
            event: Evento de dominio a publicar

        Note:
            Los handlers deben ser idempotentes. El event_id único permite
            deduplicación en handlers si es necesario.
        """
        handlers = self._subscribers.get(event.event_type, [])

        logger.info(
            "Publishing event: %s",
            event.event_type,
            extra={
                "event_id": event.event_id,
                "correlation_id": event.correlation_id,
                "aggregate_id": event.aggregate_id,
                "handlers_count": len(handlers),
            },
        )

        for handler in handlers:
            try:
                await handler.handle(event)
                logger.debug(
                    "Handler %s processed event %s",
                    handler.__class__.__name__,
                    event.event_type,
                    extra={
                        "event_id": event.event_id,
                        "correlation_id": event.correlation_id,
                    },
                )
            except Exception as e:
                # Log error pero continuar con otros handlers (test 5)
                logger.error(
                    "Handler %s failed for event %s: %s",
                    handler.__class__.__name__,
                    event.event_type,
                    str(e),
                    extra={
                        "event_id": event.event_id,
                        "correlation_id": event.correlation_id,
                        "error": str(e),
                    },
                    exc_info=True,
                )

    def get_subscribers(self, event_type: str) -> List[EventHandler]:
        """
        Obtener lista de handlers suscritos a un tipo de evento.

        Args:
            event_type: Tipo de evento

        Returns:
            Lista de handlers (vacía si no hay suscriptores)
        """
        return self._subscribers.get(event_type, [])
