"""Contract tests para eventos de dominio de auth (T-57.4).

Valida que los schemas de los eventos publicados por el módulo auth son
consistentes y no tienen regresiones de estructura. Estos tests actúan como
"contrato" entre el publisher (auth) y cualquier consumer futuro (notifications,
audit, analytics).

Si un consumer espera `payload["email"]` en `UserRegistered` y alguien elimina
ese campo, estos tests fallan en CI antes de que el consumer lo detecte en producción.

Eventos cubiertos (T-28.19):
    - UserRegistered   → payload: {user_id, email}
    - EmailVerified    → payload: {user_id, email}
    - PasswordChanged  → payload: {user_id}
    - TwoFAEnabled     → payload: {user_id}
    - TwoFADisabled    → payload: {user_id}

Contratos validados por evento:
    1. event_type es el string esperado (identificador del contrato)
    2. aggregate_type == "User"
    3. version == 1 (cambios breaking deben incrementar la versión)
    4. payload contiene exactamente los campos requeridos (ni más ni menos)
    5. event_id y correlation_id son UUIDs válidos
    6. occurred_at es timezone-aware (UTC)
    7. El evento hereda de DomainEvent
"""
from datetime import timezone
from uuid import UUID

import pytest

from app.v1.auth.domain.events.email_verified import EmailVerified
from app.v1.auth.domain.events.password_changed import PasswordChanged
from app.v1.auth.domain.events.two_fa_disabled import TwoFADisabled
from app.v1.auth.domain.events.two_fa_enabled import TwoFAEnabled
from app.v1.auth.domain.events.user_registered import UserRegistered
from app.v1.shared.domain.events import DomainEvent

# ---------------------------------------------------------------------------
# Constantes del contrato
# ---------------------------------------------------------------------------
_USER_ID = "contract-user-123"
_EMAIL = "contract@example.com"
_CORRELATION_ID = "550e8400-e29b-41d4-a716-446655440000"
_AGGREGATE_TYPE = "User"
_VERSION = 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_base_contract(event: DomainEvent, expected_type: str) -> None:
    """Valida los campos base del contrato DomainEvent."""
    assert isinstance(
        event, DomainEvent), f"{type(event).__name__} debe heredar de DomainEvent"
    assert event.event_type == expected_type
    assert event.aggregate_type == _AGGREGATE_TYPE
    assert event.aggregate_id == _USER_ID
    assert event.version == _VERSION
    # UUIDs válidos
    UUID(event.event_id)        # lanza ValueError si no es UUID válido
    UUID(event.correlation_id)  # lanza ValueError si no es UUID válido
    # Timezone-aware
    assert event.occurred_at.tzinfo is not None, "occurred_at debe ser timezone-aware"
    assert event.occurred_at.tzinfo == timezone.utc or event.occurred_at.utcoffset(
    ).total_seconds() == 0


# ---------------------------------------------------------------------------
# Contract Tests: UserRegistered
# ---------------------------------------------------------------------------

class TestUserRegisteredContract:
    """Contrato del evento UserRegistered — publisher: RegisterUser use case."""

    @pytest.fixture
    def event(self) -> UserRegistered:
        """Instancia del evento con datos de contrato."""
        return UserRegistered(
            user_id=_USER_ID,
            email=_EMAIL,
            correlation_id=_CORRELATION_ID,
        )

    def test_event_type_is_user_registered(self, event: UserRegistered):
        """event_type debe ser exactamente 'UserRegistered'."""
        assert event.event_type == "UserRegistered"

    def test_inherits_from_domain_event(self, event: UserRegistered):
        """UserRegistered debe heredar de DomainEvent."""
        assert isinstance(event, DomainEvent)

    def test_aggregate_type_is_user(self, event: UserRegistered):
        """aggregate_type debe ser 'User'."""
        assert event.aggregate_type == _AGGREGATE_TYPE

    def test_version_is_1(self, event: UserRegistered):
        """version debe ser 1 — cambios breaking deben incrementarla."""
        assert event.version == _VERSION

    def test_payload_contains_user_id(self, event: UserRegistered):
        """payload debe contener 'user_id' — requerido por consumers."""
        assert "user_id" in event.payload
        assert event.payload["user_id"] == _USER_ID

    def test_payload_contains_email(self, event: UserRegistered):
        """payload debe contener 'email' — requerido por consumers (notificaciones)."""
        assert "email" in event.payload
        assert event.payload["email"] == _EMAIL

    def test_payload_has_no_extra_fields(self, event: UserRegistered):
        """payload no debe tener campos extra no documentados en el contrato."""
        assert set(event.payload.keys()) == {"user_id", "email"}

    def test_base_contract(self, event: UserRegistered):
        """Valida todos los campos base del contrato DomainEvent."""
        _assert_base_contract(event, "UserRegistered")


# ---------------------------------------------------------------------------
# Contract Tests: EmailVerified
# ---------------------------------------------------------------------------

class TestEmailVerifiedContract:
    """Contrato del evento EmailVerified — publisher: VerifyEmail use case."""

    @pytest.fixture
    def event(self) -> EmailVerified:
        """Instancia del evento con datos de contrato."""
        return EmailVerified(
            user_id=_USER_ID,
            email=_EMAIL,
            correlation_id=_CORRELATION_ID,
        )

    def test_event_type_is_email_verified(self, event: EmailVerified):
        """event_type debe ser exactamente 'EmailVerified'."""
        assert event.event_type == "EmailVerified"

    def test_version_is_1(self, event: EmailVerified):
        """version debe ser 1."""
        assert event.version == _VERSION

    def test_payload_contains_user_id(self, event: EmailVerified):
        """payload debe contener 'user_id'."""
        assert "user_id" in event.payload
        assert event.payload["user_id"] == _USER_ID

    def test_payload_contains_email(self, event: EmailVerified):
        """payload debe contener 'email'."""
        assert "email" in event.payload
        assert event.payload["email"] == _EMAIL

    def test_payload_has_no_extra_fields(self, event: EmailVerified):
        """payload no debe tener campos extra no documentados."""
        assert set(event.payload.keys()) == {"user_id", "email"}

    def test_base_contract(self, event: EmailVerified):
        """Valida todos los campos base del contrato DomainEvent."""
        _assert_base_contract(event, "EmailVerified")


# ---------------------------------------------------------------------------
# Contract Tests: PasswordChanged
# ---------------------------------------------------------------------------

class TestPasswordChangedContract:
    """Contrato del evento PasswordChanged — publisher: ChangePassword use case."""

    @pytest.fixture
    def event(self) -> PasswordChanged:
        """Instancia del evento con datos de contrato."""
        return PasswordChanged(
            user_id=_USER_ID,
            correlation_id=_CORRELATION_ID,
        )

    def test_event_type_is_password_changed(self, event: PasswordChanged):
        """event_type debe ser exactamente 'PasswordChanged'."""
        assert event.event_type == "PasswordChanged"

    def test_version_is_1(self, event: PasswordChanged):
        """version debe ser 1."""
        assert event.version == _VERSION

    def test_payload_contains_user_id(self, event: PasswordChanged):
        """payload debe contener 'user_id'."""
        assert "user_id" in event.payload
        assert event.payload["user_id"] == _USER_ID

    def test_payload_has_no_extra_fields(self, event: PasswordChanged):
        """payload no debe tener campos extra no documentados."""
        assert set(event.payload.keys()) == {"user_id"}

    def test_base_contract(self, event: PasswordChanged):
        """Valida todos los campos base del contrato DomainEvent."""
        _assert_base_contract(event, "PasswordChanged")


# ---------------------------------------------------------------------------
# Contract Tests: TwoFAEnabled
# ---------------------------------------------------------------------------

class TestTwoFAEnabledContract:
    """Contrato del evento TwoFAEnabled — publisher: Enable2FA use case."""

    @pytest.fixture
    def event(self) -> TwoFAEnabled:
        """Instancia del evento con datos de contrato."""
        return TwoFAEnabled(
            user_id=_USER_ID,
            correlation_id=_CORRELATION_ID,
        )

    def test_event_type_is_two_fa_enabled(self, event: TwoFAEnabled):
        """event_type debe ser exactamente 'TwoFAEnabled'."""
        assert event.event_type == "TwoFAEnabled"

    def test_version_is_1(self, event: TwoFAEnabled):
        """version debe ser 1."""
        assert event.version == _VERSION

    def test_payload_contains_user_id(self, event: TwoFAEnabled):
        """payload debe contener 'user_id'."""
        assert "user_id" in event.payload
        assert event.payload["user_id"] == _USER_ID

    def test_payload_has_no_extra_fields(self, event: TwoFAEnabled):
        """payload no debe tener campos extra no documentados."""
        assert set(event.payload.keys()) == {"user_id"}

    def test_base_contract(self, event: TwoFAEnabled):
        """Valida todos los campos base del contrato DomainEvent."""
        _assert_base_contract(event, "TwoFAEnabled")


# ---------------------------------------------------------------------------
# Contract Tests: TwoFADisabled
# ---------------------------------------------------------------------------

class TestTwoFADisabledContract:
    """Contrato del evento TwoFADisabled — publisher: Disable2FA use case."""

    @pytest.fixture
    def event(self) -> TwoFADisabled:
        """Instancia del evento con datos de contrato."""
        return TwoFADisabled(
            user_id=_USER_ID,
            correlation_id=_CORRELATION_ID,
        )

    def test_event_type_is_two_fa_disabled(self, event: TwoFADisabled):
        """event_type debe ser exactamente 'TwoFADisabled'."""
        assert event.event_type == "TwoFADisabled"

    def test_version_is_1(self, event: TwoFADisabled):
        """version debe ser 1."""
        assert event.version == _VERSION

    def test_payload_contains_user_id(self, event: TwoFADisabled):
        """payload debe contener 'user_id'."""
        assert "user_id" in event.payload
        assert event.payload["user_id"] == _USER_ID

    def test_payload_has_no_extra_fields(self, event: TwoFADisabled):
        """payload no debe tener campos extra no documentados."""
        assert set(event.payload.keys()) == {"user_id"}

    def test_base_contract(self, event: TwoFADisabled):
        """Valida todos los campos base del contrato DomainEvent."""
        _assert_base_contract(event, "TwoFADisabled")
