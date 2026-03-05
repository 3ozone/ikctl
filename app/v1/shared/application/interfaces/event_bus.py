"""Puertos EventBus y EventHandler (ABCs) para event-driven architecture."""
from abc import ABC, abstractmethod

from app.v1.shared.domain.events import DomainEvent


class EventHandler(ABC):
    """Puerto para handlers de eventos de dominio.

    Los handlers deben ser idempotentes: procesar el mismo evento
    múltiples veces debe producir el mismo resultado (ADR-008).
    """

    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """Procesar un evento de dominio.

        Args:
            event: Evento a procesar

        Raises:
            Exception: Los handlers pueden lanzar excepciones.
        """


class EventBus(ABC):
    """Puerto para publicar eventos de dominio.

    Los use cases dependen de esta abstracción.
    La implementación concreta (InMemoryEventBus) vive en infrastructure.
    """

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """Publicar un evento a todos los handlers suscritos.

        Args:
            event: Evento de dominio a publicar
        """
