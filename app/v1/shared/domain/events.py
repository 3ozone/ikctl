"""DomainEvent base class para event-driven architecture."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID


@dataclass
class DomainEvent:
    """
    Clase base para eventos de dominio.

    Implementa observabilidad y trazabilidad según ADR-008.

    Attributes:
        event_id: UUID único del evento (para idempotencia)
        correlation_id: UUID para correlacionar eventos de un request completo
        event_type: Tipo de evento (ej: "UserRegistered")
        aggregate_id: ID de la entidad que generó el evento
        aggregate_type: Tipo de la entidad (ej: "User")
        payload: Datos del evento (serializables a JSON)
        version: Versión del schema del evento (>= 1)
        occurred_at: Timestamp UTC cuando ocurrió el evento
        metadata: Información contextual (user_id, ip, trace_id, etc.)
    """

    event_id: str
    correlation_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    payload: Dict[str, Any]
    version: int
    occurred_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validar campos del evento."""
        # Validar UUIDs
        try:
            UUID(self.event_id)
        except (ValueError, AttributeError):
            raise ValueError("event_id debe ser un UUID válido")

        try:
            UUID(self.correlation_id)
        except (ValueError, AttributeError):
            raise ValueError("correlation_id debe ser un UUID válido")

        # Validar strings no vacíos
        if not self.event_type or not self.event_type.strip():
            raise ValueError("event_type no puede estar vacío")

        if not self.aggregate_id or not self.aggregate_id.strip():
            raise ValueError("aggregate_id no puede estar vacío")

        if not self.aggregate_type or not self.aggregate_type.strip():
            raise ValueError("aggregate_type no puede estar vacío")

        # Validar version
        if self.version < 1:
            raise ValueError("version debe ser >= 1")

        # Validar datetime UTC
        if self.occurred_at.tzinfo is None or self.occurred_at.tzinfo.utcoffset(self.occurred_at) is None:
            raise ValueError("occurred_at debe estar en UTC")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializar evento a diccionario.

        Returns:
            Dict con todos los campos del evento, occurred_at en formato ISO.
        """
        return {
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "event_type": self.event_type,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "payload": self.payload,
            "version": self.version,
            "occurred_at": self.occurred_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainEvent":
        """
        Deserializar evento desde diccionario.

        Args:
            data: Dict con campos del evento

        Returns:
            Instancia de DomainEvent

        Raises:
            ValueError: Si el formato es inválido
        """
        # Parsear occurred_at desde ISO string
        occurred_at_str = data["occurred_at"]
        occurred_at = datetime.fromisoformat(occurred_at_str)

        # Asegurar que está en UTC
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)

        return cls(
            event_id=data["event_id"],
            correlation_id=data["correlation_id"],
            event_type=data["event_type"],
            aggregate_id=data["aggregate_id"],
            aggregate_type=data["aggregate_type"],
            payload=data["payload"],
            version=data["version"],
            occurred_at=occurred_at,
            metadata=data.get("metadata", {}),
        )
