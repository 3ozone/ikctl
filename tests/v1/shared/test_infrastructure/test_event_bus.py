"""Tests para EventBus InMemory."""
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from uuid import uuid4
import pytest

from app.v1.shared.domain.events import DomainEvent
from app.v1.shared.infrastructure.event_bus import EventBus, EventHandler


class TestEventBus:
    """Tests de EventBus InMemory."""

    @pytest.mark.asyncio
    async def test_publish_event_without_subscribers(self):
        """Test 1: Publicar evento sin suscriptores no causa error."""
        event_bus = EventBus()

        event = DomainEvent(
            event_id=str(uuid4()),
            correlation_id=str(uuid4()),
            event_type="UserRegistered",
            aggregate_id="user-123",
            aggregate_type="User",
            payload={"email": "test@example.com"},
            version=1,
            occurred_at=datetime.now(timezone.utc),
            metadata={}
        )

        # No debe lanzar excepción
        await event_bus.publish(event)

    @pytest.mark.asyncio
    async def test_subscribe_and_publish_calls_handler(self):
        """Test 2: Handler suscrito es llamado cuando se publica evento."""
        event_bus = EventBus()
        handler = AsyncMock(spec=EventHandler)

        event_bus.subscribe("UserRegistered", handler)

        event = DomainEvent(
            event_id=str(uuid4()),
            correlation_id=str(uuid4()),
            event_type="UserRegistered",
            aggregate_id="user-123",
            aggregate_type="User",
            payload={"email": "test@example.com"},
            version=1,
            occurred_at=datetime.now(timezone.utc),
            metadata={}
        )

        await event_bus.publish(event)

        handler.handle.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_multiple_handlers_same_event_type(self):
        """Test 3: Múltiples handlers para mismo tipo de evento son llamados."""
        event_bus = EventBus()
        handler1 = AsyncMock(spec=EventHandler)
        handler2 = AsyncMock(spec=EventHandler)
        handler3 = AsyncMock(spec=EventHandler)

        event_bus.subscribe("UserRegistered", handler1)
        event_bus.subscribe("UserRegistered", handler2)
        event_bus.subscribe("UserRegistered", handler3)

        event = DomainEvent(
            event_id=str(uuid4()),
            correlation_id=str(uuid4()),
            event_type="UserRegistered",
            aggregate_id="user-123",
            aggregate_type="User",
            payload={"email": "test@example.com"},
            version=1,
            occurred_at=datetime.now(timezone.utc),
            metadata={}
        )

        await event_bus.publish(event)

        handler1.handle.assert_called_once_with(event)
        handler2.handle.assert_called_once_with(event)
        handler3.handle.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_unsubscribe_handler(self):
        """Test 4: Handler desuscrito no es llamado."""
        event_bus = EventBus()
        handler = AsyncMock(spec=EventHandler)

        event_bus.subscribe("UserRegistered", handler)
        event_bus.unsubscribe("UserRegistered", handler)

        event = DomainEvent(
            event_id=str(uuid4()),
            correlation_id=str(uuid4()),
            event_type="UserRegistered",
            aggregate_id="user-123",
            aggregate_type="User",
            payload={"email": "test@example.com"},
            version=1,
            occurred_at=datetime.now(timezone.utc),
            metadata={}
        )

        await event_bus.publish(event)

        handler.handle.assert_not_called()

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_stop_other_handlers(self):
        """Test 5: Excepción en un handler no detiene otros handlers."""
        event_bus = EventBus()
        handler1 = AsyncMock(spec=EventHandler)
        handler2 = AsyncMock(spec=EventHandler)
        handler3 = AsyncMock(spec=EventHandler)

        # Handler 2 lanza excepción
        handler2.handle.side_effect = Exception("Handler error")

        event_bus.subscribe("UserRegistered", handler1)
        event_bus.subscribe("UserRegistered", handler2)
        event_bus.subscribe("UserRegistered", handler3)

        event = DomainEvent(
            event_id=str(uuid4()),
            correlation_id=str(uuid4()),
            event_type="UserRegistered",
            aggregate_id="user-123",
            aggregate_type="User",
            payload={"email": "test@example.com"},
            version=1,
            occurred_at=datetime.now(timezone.utc),
            metadata={}
        )

        # No debe lanzar excepción
        await event_bus.publish(event)

        # Handler 1 y 3 deben ser llamados aunque handler 2 falle
        handler1.handle.assert_called_once_with(event)
        handler2.handle.assert_called_once_with(event)
        handler3.handle.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_different_event_types_different_handlers(self):
        """Test 6: Cada tipo de evento llama solo a sus handlers correspondientes."""
        event_bus = EventBus()
        user_handler = AsyncMock(spec=EventHandler)
        password_handler = AsyncMock(spec=EventHandler)

        event_bus.subscribe("UserRegistered", user_handler)
        event_bus.subscribe("PasswordChanged", password_handler)

        user_event = DomainEvent(
            event_id=str(uuid4()),
            correlation_id=str(uuid4()),
            event_type="UserRegistered",
            aggregate_id="user-123",
            aggregate_type="User",
            payload={"email": "test@example.com"},
            version=1,
            occurred_at=datetime.now(timezone.utc),
            metadata={}
        )

        await event_bus.publish(user_event)

        user_handler.handle.assert_called_once_with(user_event)
        password_handler.handle.assert_not_called()

    @pytest.mark.asyncio
    async def test_subscribe_same_handler_multiple_times_only_called_once(self):
        """Test 7: Handler suscrito múltiples veces solo es llamado una vez."""
        event_bus = EventBus()
        handler = AsyncMock(spec=EventHandler)

        # Suscribir el mismo handler 3 veces
        event_bus.subscribe("UserRegistered", handler)
        event_bus.subscribe("UserRegistered", handler)
        event_bus.subscribe("UserRegistered", handler)

        event = DomainEvent(
            event_id=str(uuid4()),
            correlation_id=str(uuid4()),
            event_type="UserRegistered",
            aggregate_id="user-123",
            aggregate_type="User",
            payload={"email": "test@example.com"},
            version=1,
            occurred_at=datetime.now(timezone.utc),
            metadata={}
        )

        await event_bus.publish(event)

        # Debe ser llamado solo una vez, no 3
        handler.handle.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_handler_does_not_error(self):
        """Test 8: Desuscribir handler no registrado no causa error."""
        event_bus = EventBus()
        handler = AsyncMock(spec=EventHandler)

        # No debe lanzar excepción
        event_bus.unsubscribe("UserRegistered", handler)

    @pytest.mark.asyncio
    async def test_get_subscribers_returns_handlers(self):
        """Test 9: get_subscribers retorna lista de handlers para un evento."""
        event_bus = EventBus()
        handler1 = AsyncMock(spec=EventHandler)
        handler2 = AsyncMock(spec=EventHandler)

        event_bus.subscribe("UserRegistered", handler1)
        event_bus.subscribe("UserRegistered", handler2)

        subscribers = event_bus.get_subscribers("UserRegistered")

        assert len(subscribers) == 2
        assert handler1 in subscribers
        assert handler2 in subscribers

    @pytest.mark.asyncio
    async def test_get_subscribers_empty_when_no_handlers(self):
        """Test 10: get_subscribers retorna lista vacía si no hay handlers."""
        event_bus = EventBus()

        subscribers = event_bus.get_subscribers("NonExistentEvent")

        assert subscribers == []
