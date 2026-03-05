"""Evento de dominio: UserRegistered."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.shared.domain.events import DomainEvent


class UserRegistered(DomainEvent):
    """Evento que se publica cuando un usuario se registra en el sistema."""

    def __init__(self, user_id: str, email: str, correlation_id: str) -> None:
        super().__init__(
            event_id=str(uuid4()),
            correlation_id=correlation_id,
            event_type="UserRegistered",
            aggregate_id=user_id,
            aggregate_type="User",
            payload={"user_id": user_id, "email": email},
            version=1,
            occurred_at=datetime.now(timezone.utc),
        )
