"""Tests para los eventos de dominio del módulo auth."""
from uuid import uuid4


from app.v1.auth.domain.events.user_registered import UserRegistered
from app.v1.auth.domain.events.email_verified import EmailVerified
from app.v1.auth.domain.events.password_changed import PasswordChanged
from app.v1.auth.domain.events.user_logged_in import UserLoggedIn
from app.v1.auth.domain.events.two_fa_enabled import TwoFAEnabled
from app.v1.auth.domain.events.two_fa_disabled import TwoFADisabled
from app.v1.shared.domain.events import DomainEvent


class TestUserRegistered:
    """Tests para el evento UserRegistered."""

    def test_user_registered_is_domain_event(self):
        """UserRegistered hereda de DomainEvent."""
        event = UserRegistered(
            user_id="user-123",
            email="john@example.com",
            correlation_id=str(uuid4()),
        )
        assert isinstance(event, DomainEvent)

    def test_user_registered_fields(self):
        """UserRegistered tiene los campos correctos."""
        corr_id = str(uuid4())
        event = UserRegistered(
            user_id="user-123",
            email="john@example.com",
            correlation_id=corr_id,
        )
        assert event.aggregate_id == "user-123"
        assert event.aggregate_type == "User"
        assert event.event_type == "UserRegistered"
        assert event.version == 1
        assert event.payload["email"] == "john@example.com"
        assert event.payload["user_id"] == "user-123"
        assert event.correlation_id == corr_id
        assert event.occurred_at.tzinfo is not None


class TestEmailVerified:
    """Tests para el evento EmailVerified."""

    def test_email_verified_is_domain_event(self):
        """EmailVerified hereda de DomainEvent."""
        event = EmailVerified(
            user_id="user-123",
            email="john@example.com",
            correlation_id=str(uuid4()),
        )
        assert isinstance(event, DomainEvent)

    def test_email_verified_fields(self):
        """EmailVerified tiene los campos correctos."""
        event = EmailVerified(
            user_id="user-123",
            email="john@example.com",
            correlation_id=str(uuid4()),
        )
        assert event.aggregate_id == "user-123"
        assert event.aggregate_type == "User"
        assert event.event_type == "EmailVerified"
        assert event.version == 1


class TestPasswordChanged:
    """Tests para el evento PasswordChanged."""

    def test_password_changed_is_domain_event(self):
        """PasswordChanged hereda de DomainEvent."""
        event = PasswordChanged(
            user_id="user-123",
            correlation_id=str(uuid4()),
        )
        assert isinstance(event, DomainEvent)

    def test_password_changed_fields(self):
        """PasswordChanged tiene los campos correctos."""
        event = PasswordChanged(
            user_id="user-123",
            correlation_id=str(uuid4()),
        )
        assert event.aggregate_id == "user-123"
        assert event.aggregate_type == "User"
        assert event.event_type == "PasswordChanged"
        assert event.version == 1


class TestUserLoggedIn:
    """Tests para el evento UserLoggedIn."""

    def test_user_logged_in_is_domain_event(self):
        """UserLoggedIn hereda de DomainEvent."""
        event = UserLoggedIn(
            user_id="user-123",
            correlation_id=str(uuid4()),
        )
        assert isinstance(event, DomainEvent)

    def test_user_logged_in_fields(self):
        """UserLoggedIn tiene los campos correctos."""
        event = UserLoggedIn(
            user_id="user-123",
            correlation_id=str(uuid4()),
        )
        assert event.aggregate_id == "user-123"
        assert event.aggregate_type == "User"
        assert event.event_type == "UserLoggedIn"
        assert event.version == 1


class TestTwoFAEnabled:
    """Tests para el evento TwoFAEnabled."""

    def test_two_fa_enabled_is_domain_event(self):
        """TwoFAEnabled hereda de DomainEvent."""
        event = TwoFAEnabled(
            user_id="user-123",
            correlation_id=str(uuid4()),
        )
        assert isinstance(event, DomainEvent)

    def test_two_fa_enabled_fields(self):
        """TwoFAEnabled tiene los campos correctos."""
        event = TwoFAEnabled(
            user_id="user-123",
            correlation_id=str(uuid4()),
        )
        assert event.aggregate_id == "user-123"
        assert event.aggregate_type == "User"
        assert event.event_type == "TwoFAEnabled"
        assert event.version == 1


class TestTwoFADisabled:
    """Tests para el evento TwoFADisabled."""

    def test_two_fa_disabled_is_domain_event(self):
        """TwoFADisabled hereda de DomainEvent."""
        event = TwoFADisabled(
            user_id="user-123",
            correlation_id=str(uuid4()),
        )
        assert isinstance(event, DomainEvent)

    def test_two_fa_disabled_fields(self):
        """TwoFADisabled tiene los campos correctos."""
        event = TwoFADisabled(
            user_id="user-123",
            correlation_id=str(uuid4()),
        )
        assert event.aggregate_id == "user-123"
        assert event.aggregate_type == "User"
        assert event.event_type == "TwoFADisabled"
        assert event.version == 1
