"""Evento de dominio: CredentialUpdated."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.shared.domain.events import DomainEvent


class CredentialUpdated(DomainEvent):
    """Evento que se publica cuando se actualiza una credencial existente."""

    def __init__(self, credential_id: str, user_id: str, correlation_id: str) -> None:
        super().__init__(
            event_id=str(uuid4()),
            correlation_id=correlation_id,
            event_type="CredentialUpdated",
            aggregate_id=credential_id,
            aggregate_type="Credential",
            payload={
                "credential_id": credential_id,
                "user_id": user_id,
            },
            version=1,
            occurred_at=datetime.now(timezone.utc),
        )
