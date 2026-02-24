"""Tests para DomainEvent base class."""
from datetime import datetime, timezone
from uuid import uuid4
import pytest

from app.v1.shared.domain.events import DomainEvent


class TestDomainEvent:
    """Tests de la clase base DomainEvent."""

    def test_create_domain_event_success(self):
        """Test 1: DomainEvent se crea exitosamente con todos los campos."""
        event_id = str(uuid4())
        correlation_id = str(uuid4())
        event_type = "UserRegistered"
        aggregate_id = "user-123"
        aggregate_type = "User"
        payload = {"email": "test@example.com", "name": "John Doe"}
        version = 1
        occurred_at = datetime.now(timezone.utc)
        metadata = {"user_id": "user-123", "ip": "192.168.1.1"}

        event = DomainEvent(
            event_id=event_id,
            correlation_id=correlation_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            payload=payload,
            version=version,
            occurred_at=occurred_at,
            metadata=metadata
        )

        assert event.event_id == event_id
        assert event.correlation_id == correlation_id
        assert event.event_type == event_type
        assert event.aggregate_id == aggregate_id
        assert event.aggregate_type == aggregate_type
        assert event.payload == payload
        assert event.version == version
        assert event.occurred_at == occurred_at
        assert event.metadata == metadata

    def test_event_id_must_be_valid_uuid(self):
        """Test 2: event_id debe ser un UUID válido."""
        with pytest.raises(ValueError, match="event_id debe ser un UUID válido"):
            DomainEvent(
                event_id="not-a-uuid",
                correlation_id=str(uuid4()),
                event_type="UserRegistered",
                aggregate_id="user-123",
                aggregate_type="User",
                payload={},
                version=1,
                occurred_at=datetime.now(timezone.utc),
                metadata={}
            )

    def test_correlation_id_must_be_valid_uuid(self):
        """Test 3: correlation_id debe ser un UUID válido."""
        with pytest.raises(ValueError, match="correlation_id debe ser un UUID válido"):
            DomainEvent(
                event_id=str(uuid4()),
                correlation_id="not-a-uuid",
                event_type="UserRegistered",
                aggregate_id="user-123",
                aggregate_type="User",
                payload={},
                version=1,
                occurred_at=datetime.now(timezone.utc),
                metadata={}
            )

    def test_event_type_cannot_be_empty(self):
        """Test 4: event_type no puede estar vacío."""
        with pytest.raises(ValueError, match="event_type no puede estar vacío"):
            DomainEvent(
                event_id=str(uuid4()),
                correlation_id=str(uuid4()),
                event_type="",
                aggregate_id="user-123",
                aggregate_type="User",
                payload={},
                version=1,
                occurred_at=datetime.now(timezone.utc),
                metadata={}
            )

    def test_aggregate_id_cannot_be_empty(self):
        """Test 5: aggregate_id no puede estar vacío."""
        with pytest.raises(ValueError, match="aggregate_id no puede estar vacío"):
            DomainEvent(
                event_id=str(uuid4()),
                correlation_id=str(uuid4()),
                event_type="UserRegistered",
                aggregate_id="",
                aggregate_type="User",
                payload={},
                version=1,
                occurred_at=datetime.now(timezone.utc),
                metadata={}
            )

    def test_aggregate_type_cannot_be_empty(self):
        """Test 6: aggregate_type no puede estar vacío."""
        with pytest.raises(ValueError, match="aggregate_type no puede estar vacío"):
            DomainEvent(
                event_id=str(uuid4()),
                correlation_id=str(uuid4()),
                event_type="UserRegistered",
                aggregate_id="user-123",
                aggregate_type="",
                payload={},
                version=1,
                occurred_at=datetime.now(timezone.utc),
                metadata={}
            )

    def test_version_must_be_positive(self):
        """Test 7: version debe ser >= 1."""
        with pytest.raises(ValueError, match="version debe ser >= 1"):
            DomainEvent(
                event_id=str(uuid4()),
                correlation_id=str(uuid4()),
                event_type="UserRegistered",
                aggregate_id="user-123",
                aggregate_type="User",
                payload={},
                version=0,
                occurred_at=datetime.now(timezone.utc),
                metadata={}
            )

    def test_occurred_at_must_be_utc(self):
        """Test 8: occurred_at debe estar en UTC."""
        naive_datetime = datetime(2026, 2, 24, 10, 30, 0)  # Sin timezone
        with pytest.raises(ValueError, match="occurred_at debe estar en UTC"):
            DomainEvent(
                event_id=str(uuid4()),
                correlation_id=str(uuid4()),
                event_type="UserRegistered",
                aggregate_id="user-123",
                aggregate_type="User",
                payload={},
                version=1,
                occurred_at=naive_datetime,
                metadata={}
            )

    def test_to_dict_serialization(self):
        """Test 9: DomainEvent se serializa correctamente a dict."""
        event_id = str(uuid4())
        correlation_id = str(uuid4())
        occurred_at = datetime.now(timezone.utc)

        event = DomainEvent(
            event_id=event_id,
            correlation_id=correlation_id,
            event_type="UserRegistered",
            aggregate_id="user-123",
            aggregate_type="User",
            payload={"email": "test@example.com"},
            version=1,
            occurred_at=occurred_at,
            metadata={"ip": "192.168.1.1"}
        )

        event_dict = event.to_dict()

        assert event_dict["event_id"] == event_id
        assert event_dict["correlation_id"] == correlation_id
        assert event_dict["event_type"] == "UserRegistered"
        assert event_dict["aggregate_id"] == "user-123"
        assert event_dict["aggregate_type"] == "User"
        assert event_dict["payload"] == {"email": "test@example.com"}
        assert event_dict["version"] == 1
        assert event_dict["occurred_at"] == occurred_at.isoformat()
        assert event_dict["metadata"] == {"ip": "192.168.1.1"}

    def test_from_dict_deserialization(self):
        """Test 10: DomainEvent se deserializa correctamente desde dict."""
        event_id = str(uuid4())
        correlation_id = str(uuid4())
        occurred_at = datetime.now(timezone.utc)

        event_dict = {
            "event_id": event_id,
            "correlation_id": correlation_id,
            "event_type": "UserRegistered",
            "aggregate_id": "user-123",
            "aggregate_type": "User",
            "payload": {"email": "test@example.com"},
            "version": 1,
            "occurred_at": occurred_at.isoformat(),
            "metadata": {"ip": "192.168.1.1"}
        }

        event = DomainEvent.from_dict(event_dict)

        assert event.event_id == event_id
        assert event.correlation_id == correlation_id
        assert event.event_type == "UserRegistered"
        assert event.aggregate_id == "user-123"
        assert event.aggregate_type == "User"
        assert event.payload == {"email": "test@example.com"}
        assert event.version == 1
        assert event.occurred_at.replace(
            microsecond=0) == occurred_at.replace(microsecond=0)
        assert event.metadata == {"ip": "192.168.1.1"}
