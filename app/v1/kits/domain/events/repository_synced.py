"""Evento de dominio: RepositorySynced."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.shared.domain.events import DomainEvent


class RepositorySynced(DomainEvent):
    """Evento que se publica cuando un repositorio se sincroniza correctamente con Git."""

    def __init__(
        self,
        repository_id: str,
        user_id: str,
        commit_sha: str,
        kits_created: int,
        kits_updated: int,
        kits_deleted: int,
        correlation_id: str,
    ) -> None:
        super().__init__(
            event_id=str(uuid4()),
            correlation_id=correlation_id,
            event_type="RepositorySynced",
            aggregate_id=repository_id,
            aggregate_type="Repository",
            payload={
                "repository_id": repository_id,
                "user_id": user_id,
                "commit_sha": commit_sha,
                "kits_created": kits_created,
                "kits_updated": kits_updated,
                "kits_deleted": kits_deleted,
            },
            version=1,
            occurred_at=datetime.now(timezone.utc),
        )
