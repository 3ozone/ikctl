"""Evento de dominio: KitDiscovered."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.shared.domain.events import DomainEvent


class KitDiscovered(DomainEvent):
    """Evento que se publica cuando el sync descubre un nuevo kit en un repositorio."""

    def __init__(
        self,
        kit_id: str,
        repository_id: str,
        user_id: str,
        path_in_repo: str,
        name: str,
        correlation_id: str,
    ) -> None:
        super().__init__(
            event_id=str(uuid4()),
            correlation_id=correlation_id,
            event_type="KitDiscovered",
            aggregate_id=kit_id,
            aggregate_type="Kit",
            payload={
                "kit_id": kit_id,
                "repository_id": repository_id,
                "user_id": user_id,
                "path_in_repo": path_in_repo,
                "name": name,
            },
            version=1,
            occurred_at=datetime.now(timezone.utc),
        )
