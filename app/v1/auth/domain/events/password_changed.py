"""Evento de dominio: PasswordChanged."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.shared.domain.events import DomainEvent


class PasswordChanged(DomainEvent):
    """Evento que se publica cuando un usuario cambia su contraseña."""

    def __init__(self, user_id: str, correlation_id: str) -> None:
        super().__init__(
            event_id=str(uuid4()),
            correlation_id=correlation_id,
            event_type="PasswordChanged",
            aggregate_id=user_id,
            aggregate_type="User",
            payload={"user_id": user_id},
            version=1,
            occurred_at=datetime.now(timezone.utc),
        )
