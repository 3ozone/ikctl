"""Evento de dominio: RepositoryRegistered."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.shared.domain.events import DomainEvent


class RepositoryRegistered(DomainEvent):
    """Evento que se publica cuando se registra un nuevo repositorio Git."""

    def __init__(self, repository_id: str, user_id: str, url: str, ref: str, correlation_id: str) -> None:
        super().__init__(
            event_id=str(uuid4()),
            correlation_id=correlation_id,
            event_type="RepositoryRegistered",
            aggregate_id=repository_id,
            aggregate_type="Repository",
            payload={
                "repository_id": repository_id,
                "user_id": user_id,
                "url": url,
                "ref": ref,
            },
            version=1,
            occurred_at=datetime.now(timezone.utc),
        )
